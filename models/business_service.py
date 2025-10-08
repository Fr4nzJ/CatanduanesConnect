import uuid
from datetime import datetime
from database import driver, DATABASE
import logging

logger = logging.getLogger(__name__)
from models.user import User

class Business:
    """Business model class."""

    def __init__(self, id=None, name=None, description=None, category=None,
                 location=None, latitude=None, longitude=None, email=None, phone=None,
                 website=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.category = category
        self.location = location
        # Normalize coordinate property names
        self.latitude = latitude
        self.longitude = longitude
        self.email = email
        self.phone = phone
        self.website = website
        self.created_at = created_at or datetime.now().isoformat()

    def save(self):
        try:
            if driver is None:
                logger.error('Driver not initialized when saving business')
                return False
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MERGE (b:Business {id: $id})
                    SET
                        b.name = $name,
                        b.description = $description,
                        b.category = $category,
                        b.location = $location,
                        b.latitude = $latitude,
                        b.longitude = $longitude,
                        b.email = $email,
                        b.phone = $phone,
                        b.website = $website,
                        b.created_at = $created_at
                    RETURN b
                """, self.__dict__)
                return bool(result.single())
        except Exception as e:
            logger.error(f"Error saving business: {str(e)}")
            return False

    @staticmethod
    def from_dict(data):
        """Create a Business object from a dictionary."""
        return Business(**data)

    @staticmethod
    def get_by_id(business_id):
        """Get a business by ID."""
        with driver.session(database=DATABASE) as session:
            result = session.run(
                "MATCH (b:Business {id: $id}) RETURN b",
                id=business_id
            )
            record = result.single()
            if record:
                return Business.from_dict(record["b"])
            return None

    def to_dict(self):
        """Convert business to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "created_at": self.created_at
        }

    @staticmethod
    def search(query=None, category=None, location=None, limit=10):
        """Search businesses by name, description, category, or location."""
        conditions = []
        params = {"limit": limit}

        if query:
            conditions.append("(b.name CONTAINS $query OR b.description CONTAINS $query)")
            params["query"] = query

        if category:
            conditions.append("b.category = $category")
            params["category"] = category

        if location:
            conditions.append("b.location = $location")
            params["location"] = location

        where_clause = " AND ".join(conditions) if conditions else "true"

        with driver.session(database=DATABASE) as session:
            result = session.run(
                f"""
                MATCH (b:Business)
                WHERE {where_clause}
                RETURN b
                ORDER BY b.created_at DESC
                LIMIT $limit
                """,
                **params
            )
            return [Business.from_dict(record["b"]) for record in result]

    @staticmethod
    def get_nearby(latitude, longitude, radius=5.0):
        """Get businesses within a radius (in km) of a point."""
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (b:Business)
                WITH b, point({latitude: b.latitude, longitude: b.longitude}) AS p1, 
                     point({latitude: $lat, longitude: $lng}) AS p2
                WITH b, distance(p1, p2) / 1000 AS distance
                WHERE distance <= $radius
                RETURN b, distance
                ORDER BY distance
                """,
                lat=latitude,
                lng=longitude,
                radius=radius
            )
            return [(Business.from_dict(record["b"]), record["distance"]) 
                   for record in result]

class ServiceRequest:
    """Service Request model class."""

    def __init__(self, id=None, type=None, description=None, category=None,
                 location=None, latitude=None, longitude=None, payment=None, status="open",
                 skills_required=None, user_id=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.type = type
        self.description = description
        self.category = category
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.payment = payment
        self.status = status
        self.skills_required = skills_required or []
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()

    def save(self):
        try:
            if driver is None:
                logger.error('Driver not initialized when saving service request')
                return False
            with driver.session(database=DATABASE) as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})
                    MERGE (s:ServiceRequest {id: $id})
                    SET
                        s.type = $type,
                        s.description = $description,
                        s.category = $category,
                        s.location = $location,
                        s.latitude = $latitude,
                        s.longitude = $longitude,
                        s.payment = $payment,
                        s.status = $status,
                        s.skills_required = $skills_required,
                        s.created_at = $created_at
                    MERGE (s)-[:POSTED_BY]->(u)
                    RETURN s
                """, self.__dict__)
                return bool(result.single())
        except Exception as e:
            logger.error(f"Error saving service request: {str(e)}")
            return False

    @staticmethod
    def from_dict(data, user=None):
        """Create a ServiceRequest object from a dictionary."""
        service = ServiceRequest(**data)
        service.user = user
        return service

    @staticmethod
    def get_by_id(service_id):
        """Get a service request by ID."""
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (s:ServiceRequest {id: $id})-[:POSTED_BY]->(u:User)
                RETURN s, u
                """,
                id=service_id
            )
            record = result.single()
            if record:
                return ServiceRequest.from_dict(
                    record["s"], 
                    User.from_dict(record["u"])
                )
            return None

    def to_dict(self):
        """Convert service request to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "payment": self.payment,
            "status": self.status,
            "skills_required": self.skills_required,
            "user_id": self.user_id,
            "created_at": self.created_at
        }

    @staticmethod
    def search(query=None, type=None, category=None, location=None, 
               status="open", limit=10):
        """Search service requests."""
        conditions = ["s.status = $status"]
        params = {"status": status, "limit": limit}

        if query:
            conditions.append("s.description CONTAINS $query")
            params["query"] = query

        if type:
            conditions.append("s.type = $type")
            params["type"] = type

        if category:
            conditions.append("s.category = $category")
            params["category"] = category

        if location:
            conditions.append("s.location = $location")
            params["location"] = location

        where_clause = " AND ".join(conditions)

        with driver.session(database=DATABASE) as session:
            result = session.run(
                f"""
                MATCH (s:ServiceRequest)-[:POSTED_BY]->(u:User)
                WHERE {where_clause}
                RETURN s, u
                ORDER BY s.created_at DESC
                LIMIT $limit
                """,
                **params
            )
            return [ServiceRequest.from_dict(record["s"], User.from_dict(record["u"]))
                   for record in result]

    @staticmethod
    def get_nearby(latitude, longitude, radius=5.0, status="open"):
        """Get service requests within a radius (in km) of a point."""
        with driver.session(database=DATABASE) as session:
            result = session.run(
                """
                MATCH (s:ServiceRequest)-[:POSTED_BY]->(u:User)
                WHERE s.status = $status
                WITH s, u, point({latitude: s.latitude, longitude: s.longitude}) AS p1, 
                     point({latitude: $lat, longitude: $lng}) AS p2
                WITH s, u, distance(p1, p2) / 1000 AS distance
                WHERE distance <= $radius
                RETURN s, u, distance
                ORDER BY distance
                """,
                lat=latitude,
                lng=longitude,
                radius=radius,
                status=status
            )
            return [(ServiceRequest.from_dict(record["s"], User.from_dict(record["u"])), 
                    record["distance"]) for record in result]