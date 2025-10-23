from database import get_neo4j_driver, DATABASE
import logging

logger = logging.getLogger(__name__)

def fix_user_roles():
    """
    Fix invalid user roles in the database.
    Valid roles are: 'business_owner', 'client', 'job_seeker', 'admin'
    """
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # First, update any None or invalid roles to 'job_seeker' as default
        result = session.run("""
            MATCH (u:User)
            WHERE u.role IS NULL OR NOT u.role IN ['business_owner', 'client', 'job_seeker', 'admin']
            SET u.role = 'job_seeker',
                u.verification_status = 'pending_verification'
            RETURN count(u) as updated
        """)
        updated = result.single()['updated']
        logger.info(f"Updated {updated} users with invalid or missing roles")

        # Now set verification status for any that are missing it
        result = session.run("""
            MATCH (u:User)
            WHERE u.verification_status IS NULL
            SET u.verification_status = 'pending_verification'
            RETURN count(u) as updated
        """)
        updated = result.single()['updated']
        logger.info(f"Updated {updated} users with missing verification status")

        # Show current state
        result = session.run("""
            MATCH (u:User)
            RETURN u.email, u.role, u.verification_status
            ORDER BY u.role, u.email
        """)
        
        print("\nCurrent User States:")
        print("-" * 50)
        for record in result:
            print(f"Email: {record['u.email']}")
            print(f"Role: {record['u.role']}")
            print(f"Status: {record['u.verification_status']}\n")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    fix_user_roles()