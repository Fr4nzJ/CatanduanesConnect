import logging
from database import get_neo4j_driver

# Set up logging
logger = logging.getLogger(__name__)

class JobOffer:
    def __init__(self):
        self.id = None
        self.title = None
        self.company_name = None
        self.description = None
        self.location = None
        self.salary = None
        self.category = None
        self.created_at = None
        self.status = None
        
    @staticmethod
    def search_by_keywords(query: str):
        """Search for job offers using keywords."""
        query = query.lower()
        words = query.split()
        
        cypher_query = """
        MATCH (j:JobOffer)
        WHERE j.status = 'open' AND (
            any(word IN $words WHERE toLower(j.title) CONTAINS word) OR
            any(word IN $words WHERE toLower(j.description) CONTAINS word) OR
            any(word IN $words WHERE toLower(j.location) CONTAINS word) OR
            any(word IN $words WHERE toLower(j.category) CONTAINS word)
        )
        RETURN j
        ORDER BY j.created_at DESC
        LIMIT 3
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, words=words)
                return [JobOffer.from_node(record['j']) for record in result]
        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            return []
            
    @staticmethod
    def from_node(node):
        """Create a JobOffer instance from a Neo4j node."""
        job = JobOffer()
        # Map Neo4j node properties to object attributes
        for key in node.keys():
            setattr(job, key, node.get(key))
        return job
            
    @staticmethod
    def get_all_active(category=None, location=None):
        """Get all active job offers with optional filtering."""
        conditions = ["j.status = 'open'"]        
        params = {}
        
        if category:
            conditions.append("j.category = $category")
            params['category'] = category
            
        if location:
            conditions.append("toLower(j.location) CONTAINS toLower($location)")
            params['location'] = location
            
        cypher_query = f"""
        MATCH (j:JobOffer)
        WHERE {' AND '.join(conditions)}
        RETURN j
        ORDER BY j.created_at DESC
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, params)
                return [JobOffer.from_node(record['j']) for record in result]
        except Exception as e:
            logger.error(f"Error getting active jobs: {str(e)}")
            return []
    
    @staticmethod
    def get_by_owner(email):
        """Get all job offers posted by a specific business owner."""
        cypher_query = """
        MATCH (u:User {email: $email})-[:POSTED]->(j:JobOffer)
        RETURN j
        ORDER BY j.created_at DESC
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, email=email)
                return [JobOffer.from_node(record['j']) for record in result]
        except Exception as e:
            logger.error(f"Error getting owner's jobs: {str(e)}")
            return []
    
    @staticmethod
    def create(data, owner_email):
        """Create a new job offer."""
        cypher_query = """
        MATCH (u:User {email: $owner_email})
        CREATE (j:JobOffer)
        SET j += $data
        CREATE (u)-[:POSTED]->(j)
        RETURN j
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, 
                                   owner_email=owner_email,
                                   data=data)
                return JobOffer.from_node(result.single()['j'])
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            return None
    
    @staticmethod
    def update(job_id, data):
        """Update an existing job offer."""
        cypher_query = """
        MATCH (j:JobOffer {id: $job_id})
        SET j += $data
        RETURN j
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query,
                                   job_id=job_id,
                                   data=data)
                return JobOffer.from_node(result.single()['j'])
        except Exception as e:
            logger.error(f"Error updating job: {str(e)}")
            return None
    
    @staticmethod
    def delete(job_id):
        """Delete a job offer."""
        cypher_query = """
        MATCH (j:JobOffer {id: $job_id})
        DETACH DELETE j
        """
        
        try:
            with get_neo4j_driver().session() as session:
                session.run(cypher_query, job_id=job_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting job: {str(e)}")
            return False

    @staticmethod
    def get_categories():
        """Get all unique job categories."""
        cypher_query = """
        MATCH (j:JobOffer)
        RETURN DISTINCT j.category
        ORDER BY j.category
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query)
                return [record['j.category'] for record in result]
        except Exception as e:
            logger.error(f"Error getting job categories: {str(e)}")
            return []

class ServiceRequest:
    def __init__(self):
        self.id = None
        self.title = None
        self.description = None
        self.location = None
        self.payment_offer = None
        self.category = None
        self.created_at = None
        self.status = None
    
    @staticmethod
    def from_node(node):
        """Create a ServiceRequest instance from a Neo4j node."""
        service = ServiceRequest()
        # Map Neo4j node properties to object attributes
        for key in node.keys():
            setattr(service, key, node.get(key))
        return service

    @staticmethod
    def search_by_keywords(query: str):
        """Search for service requests using keywords."""
        query = query.lower()
        words = query.split()
        
        cypher_query = """
        MATCH (s:ServiceRequest)
        WHERE s.status = 'open' AND (
            any(word IN $words WHERE toLower(s.title) CONTAINS word) OR
            any(word IN $words WHERE toLower(s.description) CONTAINS word) OR
            any(word IN $words WHERE toLower(s.location) CONTAINS word) OR
            any(word IN $words WHERE toLower(s.category) CONTAINS word)
        )
        RETURN s
        ORDER BY s.created_at DESC
        LIMIT 3
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, words=words)
                return [ServiceRequest.from_node(record['s']) for record in result]
        except Exception as e:
            logger.error(f"Error searching services: {str(e)}")
            return []
            
    @staticmethod
    def get_all_active():
        """Get all active service requests."""
        cypher_query = """
        MATCH (s:ServiceRequest)
        WHERE s.status = 'open'
        RETURN s
        ORDER BY s.created_at DESC
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query)
                return [ServiceRequest.from_node(record['s']) for record in result]
        except Exception as e:
            logger.error(f"Error getting active services: {str(e)}")
            return []
    
    @staticmethod
    def get_by_client(email):
        """Get all service requests posted by a specific client."""
        cypher_query = """
        MATCH (u:User {email: $email})-[:POSTED]->(s:ServiceRequest)
        RETURN s
        ORDER BY s.created_at DESC
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, email=email)
                return [ServiceRequest.from_node(record['s']) for record in result]
        except Exception as e:
            logger.error(f"Error getting client's services: {str(e)}")
            return []
    
    @staticmethod
    def create(data, client_email):
        """Create a new service request."""
        cypher_query = """
        MATCH (u:User {email: $client_email})
        CREATE (s:ServiceRequest)
        SET s += $data
        CREATE (u)-[:POSTED]->(s)
        RETURN s
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query,
                                   client_email=client_email,
                                   data=data)
                return ServiceRequest.from_node(result.single()['s'])
        except Exception as e:
            logger.error(f"Error creating service: {str(e)}")
            return None
    
    @staticmethod
    def update(service_id, data):
        """Update an existing service request."""
        cypher_query = """
        MATCH (s:ServiceRequest {id: $service_id})
        SET s += $data
        RETURN s
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query,
                                   service_id=service_id,
                                   data=data)
                return ServiceRequest.from_node(result.single()['s'])
        except Exception as e:
            logger.error(f"Error updating service: {str(e)}")
            return None
    
    @staticmethod
    def delete(service_id):
        """Delete a service request."""
        cypher_query = """
        MATCH (s:ServiceRequest {id: $service_id})
        DETACH DELETE s
        """
        
        try:
            with get_neo4j_driver().session() as session:
                session.run(cypher_query, service_id=service_id)
                return True
        except Exception as e:
            logger.error(f"Error deleting service: {str(e)}")
            return False

    @staticmethod
    def get_categories():
        """Get all unique service categories."""
        cypher_query = """
        MATCH (s:ServiceRequest)
        RETURN DISTINCT s.category
        ORDER BY s.category
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query)
                return [record['s.category'] for record in result]
        except Exception as e:
            logger.error(f"Error getting service categories: {str(e)}")
            return []

class Business:
    def __init__(self):
        self.id = None
        self.name = None
        self.description = None
        self.location = None
        self.business_type = None
        self.status = None
        
    @staticmethod
    def from_node(node):
        """Create a Business instance from a Neo4j node."""
        business = Business()
        # Map Neo4j node properties to object attributes
        for key in node.keys():
            setattr(business, key, node.get(key))
        return business

    @staticmethod 
    def search_by_keywords(query: str):
        """Search for businesses using keywords."""
        query = query.lower()
        words = query.split()
        
        cypher_query = """
        MATCH (b:Business)
        WHERE b.status = 'verified' AND (
            any(word IN $words WHERE toLower(b.name) CONTAINS word) OR
            any(word IN $words WHERE toLower(b.description) CONTAINS word) OR
            any(word IN $words WHERE toLower(b.location) CONTAINS word) OR
            any(word IN $words WHERE toLower(b.business_type) CONTAINS word)
        )
        RETURN b
        ORDER BY b.name
        LIMIT 3
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query, words=words)
                return [Business.from_node(record['b']) for record in result]
        except Exception as e:
            logger.error(f"Error searching businesses: {str(e)}")
            return []
            
    @staticmethod
    def get_business_types():
        """Get all unique business types."""
        cypher_query = """
        MATCH (b:Business)
        WHERE b.status = 'verified'
        RETURN DISTINCT b.business_type
        ORDER BY b.business_type
        """
        
        try:
            with get_neo4j_driver().session() as session:
                result = session.run(cypher_query)
                return [record['b.business_type'] for record in result]
        except Exception as e:
            logger.error(f"Error getting business types: {str(e)}")
            return []