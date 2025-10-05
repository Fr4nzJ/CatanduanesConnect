"""
Script to update the Neo4j schema for businesses and services with location data
"""

from database import get_neo4j_driver, DATABASE
import logging

logger = logging.getLogger(__name__)

def update_schema():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # Create unique constraints
        unique_constraints = [
            "CREATE CONSTRAINT business_name IF NOT EXISTS FOR (b:Business) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT business_email IF NOT EXISTS FOR (b:Business) REQUIRE b.email IS UNIQUE",
            "CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:JobPost) REQUIRE j.id IS UNIQUE",
            "CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.id IS UNIQUE"
        ]

        # Create indexes
        indexes = [
            "CREATE INDEX business_category IF NOT EXISTS FOR (b:Business) ON (b.category)",
            "CREATE INDEX business_location IF NOT EXISTS FOR (b:Business) ON (b.location)",
            "CREATE INDEX job_category IF NOT EXISTS FOR (j:JobPost) ON (j.category)",
            "CREATE INDEX job_location IF NOT EXISTS FOR (j:JobPost) ON (j.location)",
            "CREATE INDEX service_category IF NOT EXISTS FOR (s:ServiceRequest) ON (s.category)",
            "CREATE INDEX service_location IF NOT EXISTS FOR (s:ServiceRequest) ON (s.location)",
            "CREATE INDEX service_type IF NOT EXISTS FOR (s:ServiceRequest) ON (s.type)"
        ]

        # Add property existence constraints for Business
        business_props = [
            "CREATE CONSTRAINT business_name_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.name IS NOT NULL",
            "CREATE CONSTRAINT business_desc_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.description IS NOT NULL",
            "CREATE CONSTRAINT business_category_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.category IS NOT NULL",
            "CREATE CONSTRAINT business_location_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.location IS NOT NULL",
            "CREATE CONSTRAINT business_lat_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.lat IS NOT NULL",
            "CREATE CONSTRAINT business_lng_exists IF NOT EXISTS FOR (b:Business) REQUIRE b.lng IS NOT NULL"
        ]

        # Add property existence constraints for JobPost
        job_props = [
            "CREATE CONSTRAINT job_title_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.title IS NOT NULL",
            "CREATE CONSTRAINT job_desc_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.description IS NOT NULL",
            "CREATE CONSTRAINT job_category_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.category IS NOT NULL",
            "CREATE CONSTRAINT job_location_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.location IS NOT NULL",
            "CREATE CONSTRAINT job_lat_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.lat IS NOT NULL",
            "CREATE CONSTRAINT job_lng_exists IF NOT EXISTS FOR (j:JobPost) REQUIRE j.lng IS NOT NULL"
        ]

        # Add property existence constraints for ServiceRequest
        service_props = [
            "CREATE CONSTRAINT service_type_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.type IS NOT NULL",
            "CREATE CONSTRAINT service_desc_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.description IS NOT NULL",
            "CREATE CONSTRAINT service_category_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.category IS NOT NULL",
            "CREATE CONSTRAINT service_location_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.location IS NOT NULL",
            "CREATE CONSTRAINT service_lat_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.lat IS NOT NULL",
            "CREATE CONSTRAINT service_lng_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.lng IS NOT NULL",
            "CREATE CONSTRAINT service_payment_exists IF NOT EXISTS FOR (s:ServiceRequest) REQUIRE s.payment IS NOT NULL"
        ]

        try:
            # Execute all schema updates
            for constraint in unique_constraints:
                session.run(constraint)
                logger.info(f"Created unique constraint: {constraint}")

            for index in indexes:
                session.run(index)
                logger.info(f"Created index: {index}")

            for prop in business_props:
                session.run(prop)
                logger.info(f"Created business property constraint: {prop}")

            for prop in job_props:
                session.run(prop)
                logger.info(f"Created job property constraint: {prop}")

            for prop in service_props:
                session.run(prop)
                logger.info(f"Created service property constraint: {prop}")

            logger.info("Schema update completed successfully")

        except Exception as e:
            logger.error(f"Error updating schema: {str(e)}")
            raise

if __name__ == "__main__":
    update_schema()