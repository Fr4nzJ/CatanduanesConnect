class JobOffer:
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