import logging
from models.business_service import Business
from database import driver, DATABASE

logger = logging.getLogger(__name__)

def search_businesses(query: str = None, category: str = None, location: str = None, limit: int = 5):
    """Search for businesses in the database."""
    try:
        return Business.search(query=query, category=category, location=location, limit=limit)
    except Exception as e:
        logger.error(f"Error searching businesses: {str(e)}")
        return []

def search_jobs(query: str = None, category: str = None, location: str = None, limit: int = 5):
    """Search for jobs in the database."""
    try:
        with driver.session(database=DATABASE) as session:
            params = {"limit": limit}
            conditions = []
            
            if query:
                conditions.append("(j.title CONTAINS $query OR j.description CONTAINS $query)")
                params["query"] = query
            
            if category:
                conditions.append("j.category = $category")
                params["category"] = category
                
            if location:
                conditions.append("j.location = $location")
                params["location"] = location
                
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            
            result = session.run(
                f"""
                MATCH (j:Job)
                WHERE {where_clause}
                RETURN j
                LIMIT $limit
                """,
                params
            )
            return [dict(record["j"]) for record in result]
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
        return []

def search_services(query: str = None, category: str = None, location: str = None, limit: int = 5):
    """Search for services in the database."""
    try:
        with driver.session(database=DATABASE) as session:
            params = {"limit": limit}
            conditions = []
            
            if query:
                conditions.append("(s.name CONTAINS $query OR s.description CONTAINS $query)")
                params["query"] = query
            
            if category:
                conditions.append("s.category = $category")
                params["category"] = category
                
            if location:
                conditions.append("s.location = $location")
                params["location"] = location
                
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            
            result = session.run(
                f"""
                MATCH (s:Service)
                WHERE {where_clause}
                RETURN s
                LIMIT $limit
                """,
                params
            )
            return [dict(record["s"]) for record in result]
    except Exception as e:
        logger.error(f"Error searching services: {str(e)}")
        return []