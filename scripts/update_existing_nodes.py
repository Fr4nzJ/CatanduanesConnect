"""
Script to update existing nodes with default values
"""

from database import get_neo4j_driver, DATABASE
import logging

logger = logging.getLogger(__name__)

def update_existing_nodes():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        try:
            # Update existing Business nodes
            session.run("""
                MATCH (b:Business)
                WHERE b.latitude IS NULL OR b.longitude IS NULL OR b.location IS NULL 
                   OR b.category IS NULL OR b.description IS NULL
                SET 
                    b.latitude = COALESCE(b.latitude, 14.0800),  // Default to Catanduanes coordinates
                    b.longitude = COALESCE(b.longitude, 124.1700),
                    b.location = COALESCE(b.location, 'Virac'),
                    b.category = COALESCE(b.category, 'General'),
                    b.description = COALESCE(b.description, 'No description provided')
            """)
            logger.info("Updated existing Business nodes")

            # Update existing ServiceRequest nodes
            session.run("""
                MATCH (s:ServiceRequest)
                WHERE s.latitude IS NULL OR s.longitude IS NULL OR s.location IS NULL 
                   OR s.category IS NULL OR s.description IS NULL OR s.type IS NULL
                   OR s.payment IS NULL
                SET 
                    s.latitude = COALESCE(s.latitude, 14.0800),
                    s.longitude = COALESCE(s.longitude, 124.1700),
                    s.location = COALESCE(s.location, 'Virac'),
                    s.category = COALESCE(s.category, 'General'),
                    s.description = COALESCE(s.description, 'No description provided'),
                    s.type = COALESCE(s.type, 'General'),
                    s.payment = COALESCE(s.payment, 'Not specified')
            """)
            logger.info("Updated existing ServiceRequest nodes")

        except Exception as e:
            logger.error(f"Error updating existing nodes: {str(e)}")
            raise

if __name__ == "__main__":
    update_existing_nodes()