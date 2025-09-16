from neo4j import GraphDatabase
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

# Neo4j Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Fr4nzJermido"

# Initialize Neo4j driver
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

class User(UserMixin):
    def __init__(self, id=None, email=None, password=None, name=None, role=None, phone=None, address=None, skills=None, experience=None, education=None, resume_path=None):
        self.id = id
        self.email = email
        self.password = password
        self.name = name
        self.role = role or "user"
        self.phone = phone
        self.address = address
        self.skills = skills or []
        self.experience = experience or []
        self.education = education or []
        self.resume_path = resume_path

    def get_id(self):
        return str(self.id)

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
        with driver.session() as session:
            result = session.run(
                """
                CREATE (u:User {
                    id: $id,
                    email: $email,
                    password: $password,
                    name: $name,
                    role: $role,
                    phone: $phone,
                    address: $address,
                    skills: $skills,
                    experience: $experience,
                    education: $education,
                    resume_path: $resume_path
                })
                RETURN u
                """,
                id=str(uuid.uuid4()),
                email=self.email,
                password=self.password,
                name=self.name,
                role=self.role,
                phone=self.phone,
                address=self.address,
                skills=self.skills,
                experience=self.experience,
                education=self.education,
                resume_path=self.resume_path
            )
            return result.single()["u"]

    @staticmethod
    def get_by_id(user_id):
        with driver.session() as session:
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
                    password=user["password"],
                    name=user["name"],
                    role=user["role"],
                    phone=user.get("phone"),
                    address=user.get("address"),
                    skills=user.get("skills", []),
                    experience=user.get("experience", []),
                    education=user.get("education", []),
                    resume_path=user.get("resume_path")
                )
            return None

    @staticmethod
    def get_by_email(email):
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {email: $email}) RETURN u",
                email=email
            )
            record = result.single()
            if record:
                user = record["u"]
                return User(
                    id=user["id"],
                    email=user["email"],
                    password=user["password"],
                    name=user["name"],
                    role=user["role"],
                    phone=user.get("phone"),
                    address=user.get("address"),
                    skills=user.get("skills", []),
                    experience=user.get("experience", []),
                    education=user.get("education", []),
                    resume_path=user.get("resume_path")
                )
            return None

    @staticmethod
    def get_all():
        with driver.session() as session:
            result = session.run("MATCH (u:User) RETURN u")
            users = []
            for record in result:
                user = record["u"]
                users.append(User(
                    id=user["id"],
                    email=user["email"],
                    name=user["name"],
                    role=user["role"],
                    phone=user.get("phone"),
                    address=user.get("address"),
                    skills=user.get("skills", []),
                    experience=user.get("experience", []),
                    education=user.get("education", []),
                    resume_path=user.get("resume_path")
                ))
            return users

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
        with driver.session() as session:
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
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {id: $owner_id})-[:OWNS]->(b:Business)
                RETURN b
                """,
                owner_id=owner_id
            )
            record = result.single()
            if record:
                business = record["b"]
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
                        id=business["owner"]["id"],
                        email=business["owner"]["email"],
                        name=business["owner"]["name"],
                        role=business["owner"]["role"]
                    )
                )
            return None

    @staticmethod
    def get_by_id(business_id):
        with driver.session() as session:
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
                        name=owner["name"],
                        role=owner["role"]
                    )
                )
            return None

    @staticmethod
    def get_all():
        with driver.session() as session:
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
                        name=owner["name"],
                        role=owner["role"]
                    )
                ))
            return businesses

    @staticmethod
    def search(query=None, location=None, category=None):
        with driver.session() as session:
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
                        name=owner["name"],
                        role=owner["role"]
                    )
                ))
            return businesses

    def get_average_rating(self):
        try:
            with driver.session() as session:
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
    def __init__(self, id=None, title=None, description=None, requirements=None, location=None, job_type=None, salary=None, business=None, created_at=None, latitude=None, longitude=None):
        self.id = id
        self.title = title
        self.description = description
        self.requirements = requirements or []
        self.location = location
        self.job_type = job_type
        self.salary = salary
        self.business = business
        self.created_at = created_at or datetime.now()
        self.latitude = latitude
        self.longitude = longitude

    def save(self):
        with driver.session() as session:
            result = session.run(
                """
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
        with driver.session() as session:
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
        with driver.session() as session:
            result = session.run(
                """
                MATCH (j:Job)
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                OPTIONAL MATCH (u:User)-[:OWNS]->(b)
                RETURN j, b, u
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
                    )
                ))
            return jobs

    @staticmethod
    def search(query=None, location=None, job_type=None, category=None):
        with driver.session() as session:
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
        with driver.session() as session:
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
    def __init__(self, id=None, job=None, applicant=None, cover_letter=None, resume_path=None, status=None, created_at=None):
        self.id = id
        self.job = job
        self.applicant = applicant
        self.cover_letter = cover_letter
        self.resume_path = resume_path
        self.status = status or "pending"
        self.created_at = created_at or datetime.now()

    def save(self):
        with driver.session() as session:
            result = session.run(
                """
                CREATE (a:Application {
                    id: $id,
                    cover_letter: $cover_letter,
                    resume_path: $resume_path,
                    status: $status,
                    created_at: $created_at
                })
                WITH a
                MATCH (j:Job {id: $job_id})
                MATCH (u:User {id: $applicant_id})
                CREATE (u)-[:APPLIED]->(a)
                CREATE (a)-[:FOR]->(j)
                RETURN a
                """,
                id=str(uuid.uuid4()),
                cover_letter=self.cover_letter,
                resume_path=self.resume_path,
                status=self.status,
                created_at=self.created_at,
                job_id=self.job.id,
                applicant_id=self.applicant.id
            )
            return result.single()["a"]

    @staticmethod
    def get_by_id(application_id):
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a:Application {id: $id})
                OPTIONAL MATCH (u:User)-[:APPLIED]->(a)
                OPTIONAL MATCH (a)-[:FOR]->(j:Job)
                OPTIONAL MATCH (b:Business)-[:POSTED]->(j)
                RETURN a, u, j, b
                """,
                id=application_id
            )
            record = result.single()
            if record:
                application = record["a"]
                applicant = record["u"]
                job = record["j"]
                business = record["b"]
                return Application(
                    id=application["id"],
                    cover_letter=application["cover_letter"],
                    resume_path=application["resume_path"],
                    status=application["status"],
                    created_at=application["created_at"],
                    job=Job(
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
                    ),
                    applicant=User(
                        id=applicant["id"],
                        email=applicant["email"],
                        name=applicant["name"],
                        role=applicant["role"]
                    )
                )
            return None 

class Review:
    def __init__(self, id=None, business=None, user=None, rating=None, comment=None, created_at=None):
        self.id = id
        self.business = business
        self.user = user
        self.rating = rating
        self.comment = comment
        self.created_at = created_at or datetime.now()

    def save(self):
        with driver.session() as session:
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
        with driver.session() as session:
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
                        name=user["name"],
                        role=user["role"]
                    )
                ))
            return reviews

    @staticmethod
    def get_average_rating(business_id):
        with driver.session() as session:
            result = session.run(
                """
                MATCH (r:Review)-[:FOR]->(b:Business {id: $business_id})
                RETURN avg(r.rating) as avg_rating
                """,
                business_id=business_id
            )
            record = result.single()
            return record["avg_rating"] if record["avg_rating"] else 0 