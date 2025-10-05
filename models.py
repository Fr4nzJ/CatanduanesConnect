import logging
import os
import uuid
from datetime import datetime
from neo4j import GraphDatabase
from database import driver, DATABASE, get_neo4j_driver
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure we have a driver
if driver is None:
    try:
        driver = get_neo4j_driver()
    except Exception as e:
        logger.error(f'Could not initialize Neo4j driver: {str(e)}')

class Activity:
    def __init__(self, id=None, type=None, action=None, user_id=None, target_id=None, 
                 target_type=None, timestamp=None, details=None):
        self.id = id or str(uuid.uuid4())
        self.type = type  # e.g., 'user_management', 'business_verification', 'content_moderation'
        self.action = action  # e.g., 'create', 'update', 'delete', 'approve', 'deny'
        self.user_id = user_id  # ID of the user who performed the action
        self.target_id = target_id  # ID of the affected resource
        self.target_type = target_type  # Type of the affected resource
        self.timestamp = timestamp or datetime.now().isoformat()
        self.details = details or {}
    
    def save(self):
        try:
            if driver is None:
                logger.error('Driver not initialized when saving activity')
                return False
            with driver.session(database=DATABASE) as session:
                # Create Activity label and constraints if they don't exist
                session.run("CREATE CONSTRAINT activity_id IF NOT EXISTS FOR (a:Activity) REQUIRE a.id IS UNIQUE")
                
                result = session.run("""
                    MERGE (a:Activity {id: $id})
                    SET
                        a.id = $id,
                        a.type = $type,
                        a.action = $action,
                        a.user_id = COALESCE($user_id, ''),
                        a.target_id = COALESCE($target_id, ''),
                        a.target_type = COALESCE($target_type, ''),
                        a.timestamp = COALESCE($timestamp, datetime()),
                        a.details = COALESCE($details, {})
                    RETURN a
                """, {
                    'id': self.id,
                    'type': self.type,
                    'action': self.action,
                    'user_id': self.user_id,
                    'target_id': self.target_id,
                    'target_type': self.target_type,
                    'timestamp': self.timestamp,
                    'details': self.details or {}
                })
                return bool(result.single())
        except Exception as e:
            logger.error(f"Error saving activity: {str(e)}")
            return False

    @staticmethod
    def get_recent(limit=10):
        try:
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MATCH (a:Activity)
                    WITH a
                    ORDER BY a.timestamp DESC
                    LIMIT $limit
                    WITH a
                    OPTIONAL MATCH (u:User {id: a.user_id})
                    WITH a, 
                    CASE
                        WHEN u IS NOT NULL THEN
                            CASE
                                WHEN u.middle_name IS NOT NULL THEN
                                    u.first_name + ' ' + u.middle_name + ' ' + u.last_name
                                ELSE
                                    u.first_name + ' ' + u.last_name
                            END
                        ELSE 'Unknown User'
                    END as user_name
                    RETURN a, user_name
                """, {"limit": limit})
                
                activities = []
                for record in result:
                    activity = record['a']
                    activity['user_name'] = record['user_name']
                    activities.append(activity)
                return activities
        except Exception as e:
            logger.error(f"Error fetching recent activities: {str(e)}")
            return []

class Notification:
    TYPES = ['info', 'success', 'warning', 'error']
    
    def __init__(self, id=None, message=None, type='info', status='unread', 
                 user_id=None, created_at=None, link=None):
        self.id = id or str(uuid.uuid4())
        self.message = message
        self.type = type if type in self.TYPES else 'info'
        self.status = status
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
        self.link = link

    @staticmethod
    def create(user_id, message, type='info', link=None):
        notification = Notification(
            message=message,
            type=type,
            user_id=user_id,
            link=link
        )
        notification.save()
        return notification

    def save(self):
        with driver.session(database=DATABASE) as session:
            session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (n:Notification {
                    id: $id,
                    message: $message,
                    type: $type,
                    status: $status,
                    created_at: $created_at,
                    link: $link
                })
                CREATE (u)-[:HAS_NOTIFICATION]->(n)
            """, self.__dict__)

    def mark_as_read(self):
        with driver.session(database=DATABASE) as session:
            session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification {id: $id})
                SET n.status = 'read'
            """, {'id': self.id, 'user_id': self.user_id})
            self.status = 'read'

    @staticmethod
    def get_user_notifications(user_id, limit=10, unread_only=False):
        with driver.session(database=DATABASE) as session:
            query = """
                MATCH (u:User {id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification)
                WHERE CASE WHEN $unread_only = true THEN n.status = 'unread' ELSE true END
                RETURN n
                ORDER BY n.created_at DESC
                LIMIT $limit
            """
            result = session.run(query, {
                'user_id': user_id,
                'unread_only': unread_only,
                'limit': limit
            })
            
            notifications = []
            for record in result:
                node = record['n']
                notification = Notification(
                    id=node['id'],
                    message=node['message'],
                    type=node['type'],
                    status=node['status'],
                    user_id=user_id,
                    created_at=node['created_at'],
                    link=node.get('link')
                )
                notifications.append(notification)
            return notifications

    @staticmethod
    def get_unread_count(user_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification)
                WHERE n.status = 'unread'
                RETURN count(n) as count
            """, {'user_id': user_id})
            return result.single()['count']

class Service:
    def __init__(self, id=None, title=None, description=None, category=None, budget=None, 
                 duration=None, location=None, requirements=None, client_id=None, 
                 status='open', created_at=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.category = category
        self.budget = budget
        self.duration = duration
        self.location = location
        self.requirements = requirements
        self.client_id = client_id
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.offers = []

    def save(self):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MERGE (s:Service {id: $id})
                SET s += {
                    title: $title,
                    description: $description,
                    category: $category,
                    budget: $budget,
                    duration: $duration,
                    location: $location,
                    requirements: $requirements,
                    status: $status,
                    created_at: $created_at
                }
                WITH s
                MATCH (c:User {id: $client_id})
                MERGE (s)-[:REQUESTED_BY]->(c)
                RETURN s
                """,
                id=self.id,
                title=self.title,
                description=self.description,
                category=self.category,
                budget=self.budget,
                duration=self.duration,
                location=self.location,
                requirements=self.requirements,
                status=self.status,
                created_at=self.created_at,
                client_id=self.client_id
            )
            record = result.single()
            if record:
                return self
            return None

    @staticmethod
    def get_by_id(service_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (s:Service {id: $id})
                OPTIONAL MATCH (s)-[:REQUESTED_BY]->(c:User)
                OPTIONAL MATCH (o:ServiceOffer)-[:OFFERS_FOR]->(s)
                OPTIONAL MATCH (o)-[:OFFERED_BY]->(j:User)
                RETURN s, c as client,
                    collect({user: j, offer: o}) as offers
                """,
                id=service_id
            )
            record = result.single()
            if record and record['s']:
                service = Service(**record['s'])
                service.client = User(**record['client']) if record['client'] else None
                service.offers = [
                    {
                        'user': User(**offer['user']),
                        'status': offer['offer']['status'],
                        'proposal': offer['offer']['proposal'],
                        'price': offer['offer']['price'],
                        'created_at': offer['offer']['created_at']
                    }
                    for offer in record['offers']
                    if offer['user'] is not None
                ]
                return service
            return None

    @staticmethod
    def get_all(status=None, client_id=None):
        with driver.session(database=DATABASE) as session:
            try:
                if client_id:
                    # When looking for a specific client's services, use MATCH to ensure proper relationship
                    query = """
                        MATCH (u:User {id: $client_id})-[:REQUESTED]->(s:Service)
                        WHERE 1=1
                    """
                else:
                    # When getting all services, just match Service nodes
                    query = """
                        MATCH (s:Service)
                        WHERE 1=1
                    """
                
                params = {'client_id': client_id} if client_id else {}
                
                if status:
                    query += " AND s.status = $status"
                    params['status'] = status
                
                query += " RETURN s ORDER BY s.created_at DESC"
                
                result = session.run(query, params)
                return [Service(**record["s"]) for record in result]
            except Exception as e:
                logger.error(f'Error in Service.get_all: {str(e)}')
                return []
            
            result = session.run(query, **params)
            return [Service(**record['s']) for record in result]

    def add_offer(self, job_seeker_id, proposal, price):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (s:Service {id: $service_id})
                MATCH (j:User {id: $job_seeker_id})
                WHERE s.status = 'open'
                MERGE (j)-[o:OFFERS]->(s)
                SET o += {
                    status: 'pending',
                    proposal: $proposal,
                    price: $price,
                    created_at: $created_at
                }
                RETURN o
                """,
                service_id=self.id,
                job_seeker_id=job_seeker_id,
                proposal=proposal,
                price=price,
                created_at=datetime.now().isoformat()
            )
            return result.single() is not None

    def accept_offer(self, job_seeker_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (j:User {id: $job_seeker_id})-[o:OFFERS]->(s:Service {id: $service_id})
                WHERE s.status = 'open'
                SET o.status = 'accepted',
                    s.status = 'in_progress'
                WITH s
                MATCH (other:User)-[r:OFFERS]->(s)
                WHERE other.id <> $job_seeker_id
                SET r.status = 'rejected'
                RETURN s
                """,
                service_id=self.id,
                job_seeker_id=job_seeker_id
            )
            return result.single() is not None

    @staticmethod
    def get_offers_by_job_seeker(job_seeker_id):
        # Note: Service offers functionality is not yet implemented
        # This method returns empty list until the OFFERS relationship is properly implemented
        return []
class User(UserMixin):
    ROLES = ['business_owner', 'client', 'job_seeker', 'admin']  # admin is here but not available for signup
    SIGNUP_ROLES = ['business_owner', 'client', 'job_seeker']  # roles available during signup
    
    def __init__(self, id=None, email=None, password=None, first_name=None, last_name=None, middle_name=None,
                 suffix=None, role=None, phone=None, address=None, skills=None, experience=None,
                 education=None, resume_path=None, permit_path=None, id_front_path=None, id_back_path=None,
                 verification_status='pending_verification',
                 google_id=None, profile_picture=None, name=None, verification_notes=None, 
                 verified_by=None, verified_at=None, is_admin=False):
        # Handle legacy name field
        if name and not any([first_name, last_name]):
            name_parts = name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                if len(name_parts) > 2:
                    middle_name = ' '.join(name_parts[1:-1])
        self.id = id or str(uuid.uuid4())
        self.email = email
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.suffix = suffix
        self.role = role if role in self.ROLES else 'job_seeker'
        self.phone = phone
        self.address = address
        self.skills = skills or []
        self.experience = experience or []
        self.education = education or []
        self.resume_path = resume_path
        self.permit_path = permit_path
        self.id_front_path = id_front_path
        self.id_back_path = id_back_path
        self.verification_status = verification_status or 'pending_verification'  # pending_verification, verified, rejected
        self.verification_notes = verification_notes
        self.verified_by = verified_by
        self.verified_at = verified_at
        self.is_admin = is_admin
        self.google_id = google_id  # Added for Google OAuth
        self.profile_picture = profile_picture  # Added for Google profile picture

    @property
    def names(self):
        """Return a dict containing all name components"""
        return {
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'full_name': self.name
        }

    @property
    def name(self):
        """Return the full name as a string"""
        name_parts = []
        if self.first_name:
            name_parts.append(self.first_name)
        if self.middle_name:
            name_parts.append(self.middle_name)
        if self.last_name:
            name_parts.append(self.last_name)
        if self.suffix:
            name_parts.append(self.suffix)
        return ' '.join(name_parts) if name_parts else None

    def get_id(self):
        return str(self.id)

    @property
    def is_verified(self):
        return self.verification_status == 'verified'

    @classmethod
    def get_by_email(cls, email):
        """Retrieve a user by their email address as a classmethod."""
        try:
            if driver is None:
                logger.error('Driver not initialized when getting user by email')
                return None

            with driver.session(database=DATABASE) as session:
                result = session.run(
                    "MATCH (u:User {email: $email}) RETURN u",
                    email=email
                )
                record = result.single()
                if record and record.get('u'):
                    node_data = dict(record['u']) if hasattr(record['u'], 'items') else record['u']
                    return cls.from_neo4j(node_data)
                return None

        except Exception as e:
            logger.error(f'Error retrieving user by email: {str(e)}')
            return None

    def verify(self, admin_email, notes=None):
        try:
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})
                    SET u.verification_status = 'verified',
                        u.verification_notes = $notes,
                        u.verified_by = $admin_email,
                        u.verified_at = datetime()
                    RETURN u
                """, {
                    'user_id': self.id,
                    'notes': notes,
                    'admin_email': admin_email
                })
                user_data = result.single()
                if user_data:
                    self.verification_status = 'verified'
                    self.verification_notes = notes
                    self.verified_by = admin_email
                    self.verified_at = datetime.now().isoformat()
                    return True
            return False
        except Exception as e:
            logger.error(f'Error verifying user: {str(e)}')
            return False

    def reject(self, admin_email, notes):
        try:
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})
                    SET u.verification_status = 'rejected',
                        u.verification_notes = $notes,
                        u.verified_by = $admin_email,
                        u.verified_at = datetime()
                    RETURN u
                """, {
                    'user_id': self.id,
                    'notes': notes,
                    'admin_email': admin_email
                })
                user_data = result.single()
                if user_data:
                    self.verification_status = 'rejected'
                    self.verification_notes = notes
                    self.verified_by = admin_email
                    self.verified_at = datetime.now().isoformat()
                    return True
            return False
        except Exception as e:
            logger.error(f'Error rejecting user: {str(e)}')
            return False

    @staticmethod
    def get_pending_verifications():
        try:
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MATCH (u:User)
                    WHERE u.verification_status = 'pending_verification'
                    RETURN u
                    ORDER BY u.created_at DESC
                """)
                return [User.from_neo4j(record['u']) for record in result]
        except Exception as e:
            logger.error(f'Error getting pending verifications: {str(e)}')
            return []

    def to_dict(self):
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        if self.suffix:
            name_parts.append(self.suffix)
            
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'suffix': self.suffix,
            'name': ' '.join(name_parts),
            'role': self.role,
            'phone': self.phone,
            'address': self.address,
            'skills': self.skills,
            'experience': self.experience,
            'education': self.education,
            'verification_status': self.verification_status,
            'resume_path': self.resume_path,
            'permit_path': self.permit_path
        }

    def set_password(self, password):
        if password:
            self.password = generate_password_hash(password)
        else:
            self.password = None

    def check_password(self, password):
        if not self.password:
            return False
        return check_password_hash(self.password, password)

    def save(self):
        try:
            # Generate ID for new users
            if not self.id:
                self.id = str(uuid.uuid4())
                
            # Prevent setting role to admin via save except for hardcoded admin email
            if self.email != 'ermido09@gmail.com':
                self.role = self.role if self.role in self.SIGNUP_ROLES else 'job_seeker'
                
            if driver is None:
                logger.error('Driver not initialized when saving user')
                return False

            with driver.session(database=DATABASE) as session:
                # Prepare user data
                user_data = {
                    'id': self.id,
                    'email': self.email,
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'middle_name': self.middle_name,
                    'suffix': self.suffix,
                    'role': self.role,
                    'phone': self.phone,
                    'address': self.address,
                    'skills': self.skills or [],
                    'experience': self.experience or [],
                    'education': self.education or [],
                    'resume_path': self.resume_path,
                    'permit_path': self.permit_path,
                    'verification_status': self.verification_status,
                    'verification_notes': self.verification_notes,
                    'verified_by': self.verified_by,
                    'verified_at': self.verified_at,
                    'is_admin': self.is_admin,
                    'google_id': self.google_id,
                    'profile_picture': self.profile_picture
                }
                
                # Add password if set
                if self.password:
                    user_data['password'] = self.password
                    
                # Create or update user
                result = session.run(
                    """
                    MERGE (u:User {id: $id})
                    SET u += $user_data
                    RETURN u
                    """,
                    id=self.id,
                    user_data=user_data
                )
                return result.single() is not None
        except Exception as e:
            logger.error(f'Error saving user: {str(e)}')
            return False

    @staticmethod
    def get_by_id(user_id):
        try:
            if driver is None:
                logger.error('Driver not initialized when getting user by id')
                return None
            with driver.session(database=DATABASE) as session:
                result = session.run(
                    "MATCH (u:User {id: $id}) RETURN u",
                    id=user_id
                )
                record = result.single()
                if record:
                    user = record["u"]
                    return User(
                        id=user["id"],
                        email=user["email"],
                        password=user.get("password"),
                        first_name=user.get("first_name"),
                        last_name=user.get("last_name"),
                        middle_name=user.get("middle_name"),
                        suffix=user.get("suffix"),
                        role=user.get("role", "job_seeker"),
                        phone=user.get("phone"),
                        address=user.get("address"),
                        skills=user.get("skills", []),
                        experience=user.get("experience", []),
                        education=user.get("education", []),
                        resume_path=user.get("resume_path"),
                        permit_path=user.get("permit_path"),
                        verification_status=user.get("verification_status", "pending_verification"),
                        google_id=user.get("google_id"),
                        profile_picture=user.get("profile_picture"),
                        verification_notes=user.get("verification_notes"),
                        verified_by=user.get("verified_by"),
                        verified_at=user.get("verified_at"),
                        is_admin=user.get("is_admin", False)
                    )
                return None
        except Exception as e:
            logger.error(f'Error getting user by id: {str(e)}')
            return None

    # Use the classmethod `get_by_email` defined earlier. The duplicate staticmethod was removed
    # to prevent confusion and accidental shadowing of the class-level method.
        except Exception as e:
            logger.error(f'Error getting user by email: {str(e)}')
            return None

    @classmethod
    def from_neo4j(cls, node_data):
        """Create a User instance from Neo4j node data"""
        return cls(
            id=node_data.get("id"),
            email=node_data.get("email"),
            password=node_data.get("password"),
            first_name=node_data.get("first_name"),
            last_name=node_data.get("last_name"),
            middle_name=node_data.get("middle_name"),
            suffix=node_data.get("suffix"),
            role=node_data.get("role", "job_seeker"),
            phone=node_data.get("phone"),
            address=node_data.get("address"),
            skills=node_data.get("skills", []),
            experience=node_data.get("experience", []),
            education=node_data.get("education", []),
            resume_path=node_data.get("resume_path"),
            permit_path=node_data.get("permit_path"),
            id_front_path=node_data.get("id_front_path"),
            id_back_path=node_data.get("id_back_path"),
            verification_status=node_data.get("verification_status", "pending_verification"),
            google_id=node_data.get("google_id"),
            profile_picture=node_data.get("profile_picture"),
            verification_notes=node_data.get("verification_notes"),
            verified_by=node_data.get("verified_by"),
            verified_at=node_data.get("verified_at"),
            is_admin=node_data.get("is_admin", False)
        )
    @classmethod
    def get_by_google_id(cls, google_id):
        """Retrieve a user by their Google account id."""
        try:
            if driver is None:
                logger.error('Driver not initialized when getting user by google_id')
                return None

            with driver.session(database=DATABASE) as session:
                result = session.run(
                    "MATCH (u:User {google_id: $google_id}) RETURN u",
                    google_id=google_id
                )
                record = result.single()
                if record and record.get('u'):
                    node_data = dict(record['u']) if hasattr(record['u'], 'items') else record['u']
                    return cls.from_neo4j(node_data)
                return None
        except Exception as e:
            logger.error(f'Error retrieving user by google_id: {str(e)}')
            return None

    @staticmethod
    def get_all():
        try:
            if driver is None:
                logger.error('Driver not initialized when getting all users')
                return []
            with driver.session(database=DATABASE) as session:
                result = session.run("MATCH (u:User) RETURN u ORDER BY u.created_at DESC")
                return [User.from_neo4j(record["u"]) for record in result]
        except Exception as e:
            logger.error(f'Error getting all users: {str(e)}')
            return []

class Business:
    def __init__(self, id=None, name=None, description=None, location=None, category=None, phone=None, email=None, website=None, owner=None, latitude=None, longitude=None):
        self.id = id
        self.name = name
        self.description = description
        self.location = location
        self.category = category
        self.phone = phone
        self.email = email
        self.website = website
        self.owner = owner
        self.latitude = latitude
        self.longitude = longitude

    def save(self):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                CREATE (b:Business {
                    id: $id,
                    name: $name,
                    description: $description,
                    location: $location,
                    category: $category,
                    phone: $phone,
                    email: $email,
                    website: $website,
                    latitude: $latitude,
                    longitude: $longitude
                })
                WITH b
                MATCH (u:User {id: $owner_id})
                CREATE (u)-[:OWNS]->(b)
                RETURN b
                """,
                id=str(uuid.uuid4()),
                name=self.name,
                description=self.description,
                location=self.location,
                category=self.category,
                phone=self.phone,
                email=self.email,
                website=self.website,
                latitude=self.latitude,
                longitude=self.longitude,
                owner_id=self.owner.id
            )
            return result.single()["b"]

    @staticmethod
    def get_by_owner_id(owner_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (u:User {id: $owner_id})-[:OWNS]->(b:Business)
                RETURN b, u as owner
                """,
                owner_id=owner_id
            )
            record = result.single()
            if record:
                business = record["b"]
                owner = record["owner"]
                return Business(
                    id=business["id"],
                    name=business["name"],
                    description=business["description"],
                    location=business["location"],
                    category=business["category"],
                    phone=business["phone"],
                    email=business["email"],
                    website=business.get("website"),
                    latitude=business.get("latitude"),
                    longitude=business.get("longitude"),
                    owner=User(
                        id=owner["id"],
                        email=owner["email"],
                        first_name=owner.get("first_name"),
                        last_name=owner.get("last_name"),
                        role=owner["role"]
                    )
                )
            return None

    @staticmethod
    def get_by_id(business_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (b:Business {id: $id})
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                RETURN b, u
                """,
                id=business_id
            )
            record = result.single()
            if record:
                business = record["b"]
                owner = record["u"]
                return Business(
                    id=business["id"],
                    name=business["name"],
                    description=business["description"],
                    location=business["location"],
                    category=business["category"],
                    phone=business["phone"],
                    email=business["email"],
                    website=business.get("website"),
                    latitude=business.get("latitude"),
                    longitude=business.get("longitude"),
                    owner=User(
                        id=owner["id"],
                        email=owner["email"],
                        first_name=owner.get("first_name"),
                        last_name=owner.get("last_name"),
                        role=owner["role"]
                    ) if owner else None
                )
            return None

    @staticmethod
    def get_all():
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (b:Business)
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                RETURN b, u
                """
            )
            businesses = []
            for record in result:
                business = record["b"]
                owner = record["u"]
                businesses.append(Business(
                    id=business["id"],
                    name=business["name"],
                    description=business["description"],
                    location=business["location"],
                    category=business["category"],
                    phone=business["phone"],
                    email=business["email"],
                    website=business.get("website"),
                    latitude=business.get("latitude"),
                    longitude=business.get("longitude"),
                    owner=User(
                        id=owner["id"],
                        email=owner["email"],
                        first_name=owner.get("first_name"),
                        last_name=owner.get("last_name"),
                        middle_name=owner.get("middle_name"),
                        suffix=owner.get("suffix"),
                        role=owner["role"],
                        name=owner.get("name")  # Fallback for legacy data
                    )
                ))
            return businesses

    @staticmethod
    def search(query=None, location=None, category=None):
        with driver.session(database=DATABASE) as session:
            cypher_query = """
                MATCH (b:Business)
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                WHERE 1=1
            """
            params = {}

            if query:
                cypher_query += """
                    AND (
                        b.name CONTAINS $query
                        OR b.description CONTAINS $query
                    )
                """
                params["query"] = query

            if location:
                cypher_query += " AND b.location = $location"
                params["location"] = location

            if category:
                cypher_query += " AND b.category = $category"
                params["category"] = category

            cypher_query += """
                RETURN b, u
            """

            result = session.run(cypher_query, params)
            businesses = []
            for record in result:
                business = record["b"]
                owner = record["u"]
                businesses.append(Business(
                    id=business["id"],
                    name=business["name"],
                    description=business["description"],
                    location=business["location"],
                    category=business["category"],
                    phone=business["phone"],
                    email=business["email"],
                    website=business.get("website"),
                    latitude=business.get("latitude"),
                    longitude=business.get("longitude"),
                    owner=User(
                        id=owner["id"],
                        email=owner["email"],
                        first_name=owner.get("first_name"),
                        last_name=owner.get("last_name"),
                        middle_name=owner.get("middle_name"),
                        suffix=owner.get("suffix"),
                        role=owner["role"],
                        name=owner.get("name")  # Fallback for legacy data
                    )
                ))
            return businesses

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'category': self.category,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'owner': self.owner.to_dict() if self.owner else None
        }

    def get_average_rating(self):
        try:
            with driver.session(database=DATABASE) as session:
                result = session.run(
                    """
                    MATCH (r:Review)-[:FOR]->(b:Business {id: $business_id})
                    RETURN avg(r.rating) as avg_rating
                    """,
                    business_id=self.id
                )
                record = result.single()
                avg_rating = record["avg_rating"] if record["avg_rating"] else 0
                return round(float(avg_rating), 1)
        except Exception as e:
            print(f"Error calculating average rating: {str(e)}")
            return 0.0

class Job:
    def __init__(self, id=None, title=None, description=None, requirements=None, 
                    location=None, job_type=None, salary=None, business=None,
                    created_at=None, latitude=None, longitude=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.requirements = requirements
        self.location = location
        self.job_type = job_type
        self.salary = salary
        self.business = business
        self.created_at = created_at or datetime.now()
        self.latitude = latitude
        self.longitude = longitude

    def save(self):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                CREATE (j:Job {
                    id: $id,
                    title: $title,
                    description: $description,
                    requirements: $requirements,
                    location: $location,
                    job_type: $job_type,
                    salary: $salary,
                    created_at: $created_at,
                    latitude: $latitude,
                    longitude: $longitude
                })
                WITH j
                MATCH (b:Business {id: $business_id})
                CREATE (b)-[:POSTED]->(j)
                RETURN j
                """,
                id=str(uuid.uuid4()),
                title=self.title,
                description=self.description,
                requirements=self.requirements,
                location=self.location,
                job_type=self.job_type,
                salary=self.salary,
                created_at=self.created_at.isoformat(),
                latitude=self.latitude,
                longitude=self.longitude,
                business_id=self.business.id
            )
            return result.single()["j"]

    @staticmethod
    def get_by_id(job_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (j:Job {id: $id})
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                RETURN j, b, u
                """,
                id=job_id
            )
            record = result.single()
            if record:
                job = record["j"]
                business = record["b"]
                owner = record["u"]
                return Job(
                    id=job["id"],
                    title=job["title"],
                    description=job["description"],
                    requirements=job["requirements"],
                    location=job["location"],
                    job_type=job["job_type"],
                    salary=job.get("salary"),
                    created_at=datetime.fromisoformat(job["created_at"]) if isinstance(job["created_at"], str) else job["created_at"],
                    latitude=job.get("latitude"),
                    longitude=job.get("longitude"),
                    business=Business(
                        id=business["id"],
                        name=business["name"],
                        description=business["description"],
                        location=business["location"],
                        category=business["category"],
                        phone=business["phone"],
                        email=business["email"],
                        website=business.get("website"),
                        latitude=business.get("latitude"),
                        longitude=business.get("longitude"),
                        owner=User(
                            id=owner["id"],
                            email=owner["email"],
                            name=owner["name"],
                            role=owner["role"]
                        )
                    )
                )
            return None

    @staticmethod
    def get_all():
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (j:Job)
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                RETURN j, b, u
                ORDER BY j.created_at DESC
                """
            )
            jobs = []
            for record in result:
                job = record["j"]
                business = record["b"]
                owner = record["u"]
                jobs.append(Job(
                    id=job["id"],
                    title=job["title"],
                    description=job["description"],
                    requirements=job["requirements"],
                    location=job["location"],
                    job_type=job["job_type"],
                    salary=job.get("salary"),
                    created_at=datetime.fromisoformat(job["created_at"]) if isinstance(job["created_at"], str) else job["created_at"],
                    latitude=job.get("latitude"),
                    longitude=job.get("longitude"),
                    business=Business(
                        id=business["id"],
                        name=business["name"],
                        description=business["description"],
                        location=business["location"],
                        category=business["category"],
                        phone=business["phone"],
                        email=business["email"],
                        website=business.get("website"),
                        latitude=business.get("latitude"),
                        longitude=business.get("longitude"),
                        owner=User(
                            id=owner["id"],
                            email=owner["email"],
                            name=owner["name"],
                            role=owner["role"]
                        )
                    ) if business and owner else None
                ))
                jobs.append(Job(
                    id=job["id"],
                    title=job["title"],
                    description=job["description"],
                    requirements=job["requirements"],
                    location=job["location"],
                    job_type=job["job_type"],
                    salary=job.get("salary"),
                    created_at=datetime.fromisoformat(job["created_at"]) if isinstance(job["created_at"], str) else job["created_at"],
                    latitude=job.get("latitude"),
                    longitude=job.get("longitude"),
                    business=Business(
                        id=business["id"],
                        name=business["name"],
                        description=business["description"],
                        location=business["location"],
                        category=business["category"],
                        phone=business["phone"],
                        email=business["email"],
                        website=business.get("website"),
                        latitude=business.get("latitude"),
                        longitude=business.get("longitude"),
                        owner=User(
                            id=owner["id"],
                            email=owner["email"],
                            name=owner["name"],
                            role=owner["role"]
                        )
                    )
                ))
            return jobs

    @staticmethod
    def search(query=None, location=None, job_type=None, category=None):
        with driver.session(database=DATABASE) as session:
            cypher_query = """
                MATCH (j:Job)
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                WHERE 1=1
            """
            params = {}

            if query:
                cypher_query += """
                    AND (
                        j.title CONTAINS $query
                        OR j.description CONTAINS $query
                        OR b.name CONTAINS $query
                    )
                """
                params["query"] = query

            if location:
                cypher_query += " AND j.location = $location"
                params["location"] = location

            if job_type:
                cypher_query += " AND j.job_type = $job_type"
                params["job_type"] = job_type

            if category:
                cypher_query += " AND b.category = $category"
                params["category"] = category

            cypher_query += """
                RETURN j, b
                ORDER BY j.created_at DESC
            """

            result = session.run(cypher_query, params)
            jobs = []
            for record in result:
                job = record["j"]
                business = record["b"]
                jobs.append(Job(
                    id=job["id"],
                    title=job["title"],
                    description=job["description"],
                    requirements=job["requirements"],
                    location=job["location"],
                    job_type=job["job_type"],
                    salary=job["salary"],
                    created_at=job["created_at"],
                    latitude=job.get("latitude"),
                    longitude=job.get("longitude"),
                    business=Business(
                        id=business["id"],
                        name=business["name"],
                        description=business["description"],
                        location=business["location"],
                        category=business["category"],
                        phone=business["phone"],
                        email=business["email"],
                        website=business.get("website"),
                        latitude=business.get("latitude"),
                        longitude=business.get("longitude"),
                        owner=User(
                            id=business["owner"]["id"],
                            email=business["owner"]["email"],
                            name=business["owner"]["name"],
                            role=business["owner"]["role"]
                        )
                    )
                ))
            return jobs

    @staticmethod
    def get_by_business_id(business_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (b:Business {id: $business_id})-[:POSTED]->(j:Job)
                RETURN j
                ORDER BY j.created_at DESC
                """,
                business_id=business_id
            )
            jobs = []
            for record in result:
                job = record["j"]
                jobs.append(Job(
                    id=job["id"],
                    title=job["title"],
                    description=job["description"],
                    requirements=job["requirements"],
                    location=job["location"],
                    job_type=job["job_type"],
                    salary=job["salary"],
                    created_at=job["created_at"],
                    latitude=job.get("latitude"),
                    longitude=job.get("longitude")
                ))
            return jobs

class Application:
    STATUSES = ['pending', 'accepted', 'rejected', 'withdrawn']
    
    def __init__(self, id=None, job=None, applicant=None, status=None, date_applied=None, 
                 cover_letter=None, resume_path=None, feedback=None):
        self.id = id or str(uuid.uuid4())
        self.job = job
        self.applicant = applicant
        self.status = status if status in self.STATUSES else "pending"
        self.date_applied = date_applied or datetime.now().isoformat()
        self.cover_letter = cover_letter
        self.resume_path = resume_path
        self.feedback = feedback  # Optional feedback from employer

    def save(self):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (j:Job {id: $job_id})
                MATCH (a:User {id: $applicant_id})
                MERGE (app:Application {id: $id})
                SET app.status = $status,
                    app.date_applied = $date_applied,
                    app.cover_letter = $cover_letter,
                    app.resume_path = $resume_path,
                    app.feedback = $feedback
                MERGE (a)-[:APPLIED_TO]->(app)
                MERGE (app)-[:FOR_JOB]->(j)
                RETURN app
                """,
                id=self.id,
                job_id=self.job.id,
                applicant_id=self.applicant.id,
                status=self.status,
                date_applied=self.date_applied,
                cover_letter=self.cover_letter,
                resume_path=self.resume_path,
                feedback=self.feedback
            )
            record = result.single()
            return record is not None

    @staticmethod
    def get_by_id(application_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (app:Application {id: $id})
                MATCH (a:User)-[:APPLIED_TO]->(app)-[:FOR_JOB]->(j:Job)
                RETURN app, a as applicant, j as job
                """,
                id=application_id
            )
            record = result.single()
            if record:
                application = Application(**record['app'])
                application.applicant = User(**record['applicant'])
                application.job = Job(**record['job'])
                return application
            return None

    @staticmethod
    def get_by_job_id(job_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (app:Application)-[:FOR_JOB]->(j:Job {id: $job_id})
                MATCH (a:User)-[:APPLIED_TO]->(app)
                RETURN app, a as applicant, j as job
                ORDER BY app.date_applied DESC
                """,
                job_id=job_id
            )
            return [
                {
                    'application': Application(**record['app']),
                    'applicant': User(**record['applicant']),
                    'job': Job(**record['job'])
                }
                for record in result
            ]

    @staticmethod
    def get_by_applicant_id(applicant_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (a:User {id: $applicant_id})-[:APPLIED_TO]->(app:Application)-[:FOR_JOB]->(j:Job)
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                RETURN app, a as applicant, j as job, b as business
                ORDER BY app.date_applied DESC
                """,
                applicant_id=applicant_id
            )
            return [
                {
                    'application': Application(**record['app']),
                    'job': Job(**record['job']),
                    'business': Business(**record['business']) if record['business'] else None
                }
                for record in result
            ]

    def update_status(self, new_status, feedback=None):
        if new_status not in self.STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(self.STATUSES)}")
            
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (app:Application {id: $id})
                SET app.status = $status,
                    app.feedback = $feedback
                RETURN app
                """,
                id=self.id,
                status=new_status,
                feedback=feedback
            )
            record = result.single()
            if record:
                self.status = new_status
                self.feedback = feedback
                return True
            return False

    @staticmethod
    def has_applied(applicant_id, job_id):
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (a:User {id: $applicant_id})-[:APPLIED_TO]->(app:Application)-[:FOR_JOB]->(j:Job {id: $job_id})
                RETURN app
                """,
                applicant_id=applicant_id,
                job_id=job_id
            )
            return result.single() is not None

class Review:
    def __init__(self, id=None, business=None, user=None, rating=None, comment=None, created_at=None):
        self.id = id
        self.business = business
        self.user = user
        self.rating = rating
        self.comment = comment
        self.created_at = created_at or datetime.now()

    def save(self):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                CREATE (r:Review {
                    id: $id,
                    rating: $rating,
                    comment: $comment,
                    created_at: $created_at
                })
                WITH r
                MATCH (b:Business {id: $business_id})
                MATCH (u:User {id: $user_id})
                CREATE (u)-[:WROTE]->(r)-[:FOR]->(b)
                RETURN r
                """,
                id=str(uuid.uuid4()),
                rating=self.rating,
                comment=self.comment,
                created_at=self.created_at,
                business_id=self.business.id,
                user_id=self.user.id
            )
            return result.single()["r"]

    @staticmethod
    def get_by_business_id(business_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (u:User)-[:WROTE]->(r:Review)-[:FOR]->(b:Business {id: $business_id})
                RETURN r, u
                ORDER BY r.created_at DESC
                """,
                business_id=business_id
            )
            reviews = []
            for record in result:
                review = record["r"]
                user = record["u"]
                reviews.append(Review(
                    id=review["id"],
                    rating=review["rating"],
                    comment=review["comment"],
                    created_at=review["created_at"],
                    user=User(
                        id=user["id"],
                        email=user["email"],
                        first_name=user.get("first_name"),
                        last_name=user.get("last_name"),
                        middle_name=user.get("middle_name"),
                        suffix=user.get("suffix"),
                        role=user["role"]
                    )
                ))
            return reviews

    @staticmethod
    def get_average_rating(business_id):
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (r:Review)-[:FOR]->(b:Business {id: $business_id})
                RETURN avg(r.rating) as avg_rating
                """,
                business_id=business_id
            )
            record = result.single()
            return record["avg_rating"] if record["avg_rating"] else 0 