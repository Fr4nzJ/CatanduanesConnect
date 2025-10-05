import os
import logging
import time
from neo4j import GraphDatabase, exceptions as neo4j_exceptions
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize singleton variables
_driver = None
_database = os.getenv('NEO4J_DATABASE', 'neo4j')

# Export DATABASE for other modules to use
DATABASE = _database

def get_neo4j_driver(max_retries: int = 3, backoff: float = 1.0):
    """Return a singleton Neo4j driver, retrying on transient failures.

    Reads connection details from environment variables:
    - NEO4J_URI
    - NEO4J_USERNAME
    - NEO4J_PASSWORD
    """
    global _driver
    if _driver is not None:
        return _driver

    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')

    if not all([uri, user, password]):
        logger.error('Missing Neo4j environment variables. NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD are required.')
        raise ValueError('Missing required Neo4j environment variables')

    attempt = 0
    while attempt < max_retries:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            # quick smoke test
            with driver.session(database=_database) as session:
                session.run('RETURN 1').single()
            _driver = driver
            logger.info('Connected to Neo4j successfully')
            return _driver
        except neo4j_exceptions.ServiceUnavailable as e:
            attempt += 1
            logger.warning('Neo4j ServiceUnavailable on attempt %d/%d: %s', attempt, max_retries, str(e))
            time.sleep(backoff * attempt)
        except Exception as e:
            logger.error('Unexpected error connecting to Neo4j: %s', str(e), exc_info=True)
            raise

    logger.error('Exceeded retries connecting to Neo4j')
    raise neo4j_exceptions.ServiceUnavailable('Could not connect to Neo4j after retries')


def get_database_name():
    """Return the configured Neo4j database name."""
    return _database

# Initialize the driver on module import
try:
    driver = get_neo4j_driver()
except Exception as e:
    logger.error(f"Failed to initialize Neo4j driver on module load: {str(e)}")
    driver = None

def create_business(name: str, description: str, category: str, location: str, lat: float, lng: float, email: str, phone: str = None, website: str = None):
    """Create a new business node in Neo4j."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run(
            """
            CREATE (b:Business {
                name: $name,
                description: $description,
                category: $category,
                location: $location,
                lat: $lat,
                lng: $lng,
                email: $email,
                phone: $phone,
                website: $website,
                created_at: datetime()
            })
            RETURN b
            """,
            name=name,
            description=description,
            category=category,
            location=location,
            lat=lat,
            lng=lng,
            email=email,
            phone=phone,
            website=website
        )
        return result.single()

def get_business(business_id: str):
    """Get a business by ID."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run(
            "MATCH (b:Business) WHERE ID(b) = $business_id RETURN b",
            business_id=int(business_id)
        )
        return result.single()

def search_businesses(query: str = None, category: str = None, location: str = None, limit: int = 10):
    """Search businesses by name, description, category, or location."""
    with get_neo4j_driver().session(database=DATABASE) as session:
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
        return [record["b"] for record in result]

def get_nearby_businesses(lat: float, lng: float, radius: float = 5.0):
    """Get businesses within a radius (in km) of a point."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        # Haversine formula in Cypher
        result = session.run(
            """
            MATCH (b:Business)
            WITH b, point({latitude: b.lat, longitude: b.lng}) AS p1, 
                 point({latitude: $lat, longitude: $lng}) AS p2
            WITH b, distance(p1, p2) / 1000 AS distance
            WHERE distance <= $radius
            RETURN b, distance
            ORDER BY distance
            """,
            lat=lat,
            lng=lng,
            radius=radius
        )
        return [(record["b"], record["distance"]) for record in result]

def create_service_request(type: str, description: str, category: str, location: str, lat: float, lng: float, 
                         payment: str, user_id: str, skills_required: list = None):
    """Create a new service request."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run(
            """
            MATCH (u:User) WHERE ID(u) = $user_id
            CREATE (s:ServiceRequest {
                type: $type,
                description: $description,
                category: $category,
                location: $location,
                lat: $lat,
                lng: $lng,
                payment: $payment,
                skills_required: $skills_required,
                status: 'open',
                created_at: datetime()
            })-[:POSTED_BY]->(u)
            RETURN s
            """,
            type=type,
            description=description,
            category=category,
            location=location,
            lat=lat,
            lng=lng,
            payment=payment,
            user_id=int(user_id),
            skills_required=skills_required or []
        )
        return result.single()

def search_services(query: str = None, type: str = None, category: str = None, 
                   location: str = None, status: str = "open", limit: int = 10):
    """Search service requests."""
    with get_neo4j_driver().session(database=DATABASE) as session:
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
        return [(record["s"], record["u"]) for record in result]

def get_nearby_services(lat: float, lng: float, radius: float = 5.0, status: str = "open"):
    """Get service requests within a radius (in km) of a point."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run(
            """
            MATCH (s:ServiceRequest)-[:POSTED_BY]->(u:User)
            WHERE s.status = $status
            WITH s, u, point({latitude: s.lat, longitude: s.lng}) AS p1, 
                 point({latitude: $lat, longitude: $lng}) AS p2
            WITH s, u, distance(p1, p2) / 1000 AS distance
            WHERE distance <= $radius
            RETURN s, u, distance
            ORDER BY distance
            """,
            lat=lat,
            lng=lng,
            radius=radius,
            status=status
        )
        return [(record["s"], record["u"], record["distance"]) for record in result]

def get_business_categories():
    """Get all unique business categories."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run("MATCH (b:Business) RETURN DISTINCT b.category")
        return [record["b.category"] for record in result]

def get_service_categories():
    """Get all unique service categories."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run("MATCH (s:ServiceRequest) RETURN DISTINCT s.category")
        return [record["s.category"] for record in result]

def get_locations():
    """Get all unique locations from both businesses and services."""
    with get_neo4j_driver().session(database=DATABASE) as session:
        result = session.run(
            """
            MATCH (n)
            WHERE n:Business OR n:ServiceRequest
            RETURN DISTINCT n.location
            """
        )
        return [record["n.location"] for record in result]
