"""
Script to update user roles for jobs and services functionality
"""

from database import get_neo4j_driver, DATABASE
import logging

logger = logging.getLogger(__name__)

def update_user_roles():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        try:
            # Add role property to users if they don't have it
            session.run("""
                MATCH (u:User)
                WHERE u.role IS NULL
                SET u.role = 'client'
            """)
            
            # Merge role values
            session.run("""
                MATCH (u:User)
                WHERE u.role IN ['user', 'regular', 'normal']
                SET u.role = 'client'
            """)
            
            # Add new roles to business owners
            session.run("""
                MATCH (u:User)-[:OWNS]->(b:Business)
                SET u.role = 'business_owner'
            """)
            
            # Add provider role to verified professionals
            session.run("""
                MATCH (u:User)
                WHERE u.is_verified = true
                SET u.role = 'provider'
            """)
            
            logger.info("User roles updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating user roles: {str(e)}")
            raise

if __name__ == "__main__":
    update_user_roles()