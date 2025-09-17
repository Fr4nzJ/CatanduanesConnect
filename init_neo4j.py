from models import driver, DATABASE
from datetime import datetime

def init_db():
    with driver.session(database=DATABASE) as session:
        # Create constraints for uniqueness
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE")
        session.run("CREATE CONSTRAINT business_id IF NOT EXISTS FOR (b:Business) REQUIRE b.id IS UNIQUE")
        session.run("CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:Job) REQUIRE j.id IS UNIQUE")
        session.run("CREATE CONSTRAINT application_id IF NOT EXISTS FOR (a:Application) REQUIRE a.id IS UNIQUE")
        session.run("CREATE CONSTRAINT notification_id IF NOT EXISTS FOR (n:Notification) REQUIRE n.id IS UNIQUE")
        session.run("CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE")
        session.run("CREATE CONSTRAINT review_id IF NOT EXISTS FOR (r:Review) REQUIRE r.id IS UNIQUE")
        
        # Create indexes for better performance
        session.run("CREATE INDEX user_role IF NOT EXISTS FOR (u:User) ON (u.role)")
        session.run("CREATE INDEX business_category IF NOT EXISTS FOR (b:Business) ON (b.category)")
        session.run("CREATE INDEX job_category IF NOT EXISTS FOR (j:Job) ON (j.category)")
        session.run("CREATE INDEX notification_status IF NOT EXISTS FOR (n:Notification) ON (n.status)")
        session.run("CREATE INDEX service_category IF NOT EXISTS FOR (s:Service) ON (s.category)")
        
        # Ensure all relationship types are registered
        session.run("""
            MATCH (u:User {id: 'dummy'})-[r:FOR|HAS_NOTIFICATION|WROTE|POSTED|APPLIED_TO|FOR_JOB|OWNS|OFFERS|REQUESTED]->(n)
            RETURN r LIMIT 0
        """)

if __name__ == '__main__':
    init_db()