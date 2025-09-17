from neo4j import GraphDatabase
from datetime import datetime

from dotenv import load_dotenv
import os

from neo4j import GraphDatabase
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Neo4j Configuration from environment variables
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

def clear_database():
    with driver.session(database=DATABASE) as session:
        print("Clearing database...")
        session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared.")
        
        print("Creating constraints...")
        # Create constraints
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE")
        print("Constraints created.")
        
        print("Creating default admin...")
        # Create admin user
        session.run("""
            CREATE (u:User {
                id: $id,
                email: $email,
                password: $password,
                name: $name,
                role: $role,
                verification_status: 'verified'
            })
        """, {
            "id": str(uuid.uuid4()),
            "email": "ermido09@gmail.com",
            "password": generate_password_hash("Fr4nzJermido"),
            "name": "Franz Jermido",
            "role": "admin"
        })
        print("Admin user created.")

def create_sample_data():
    with driver.session() as session:
        # Create sample users
        session.run("""
            CREATE (u1:User {
                name: 'John Doe',
                email: 'john@example.com',
                password_hash: 'dummy_hash',
                user_type: 'job_seeker',
                created_at: datetime()
            })
            CREATE (u2:User {
                name: 'Jane Smith',
                email: 'jane@example.com',
                password_hash: 'dummy_hash',
                user_type: 'business_owner',
                created_at: datetime()
            })
            CREATE (u3:User {
                name: 'Admin User',
                email: 'admin@example.com',
                password_hash: 'dummy_hash',
                user_type: 'admin',
                created_at: datetime()
            })
        """)

        # Create sample businesses
        session.run("""
            MATCH (u:User {email: 'jane@example.com'})
            CREATE (b1:Business {
                name: 'Tech Solutions Inc.',
                description: 'A leading technology company in Catanduanes',
                location: 'Virac',
                category: 'Technology',
                size: 'Medium',
                created_at: datetime()
            })
            CREATE (u)-[:OWNS]->(b1)
            
            CREATE (b2:Business {
                name: 'ABC Retail Store',
                description: 'Your one-stop shop for all your needs',
                location: 'San Andres',
                category: 'Retail',
                size: 'Small',
                created_at: datetime()
            })
            CREATE (u)-[:OWNS]->(b2)
        """)

        # Create sample jobs
        session.run("""
            MATCH (b:Business {name: 'Tech Solutions Inc.'})
            CREATE (j1:Job {
                title: 'Software Developer',
                description: 'Looking for an experienced software developer',
                requirements: 'Python, JavaScript, React',
                salary: '30000',
                job_type: 'Full Time',
                location: 'Virac',
                created_at: datetime()
            })
            CREATE (b)-[:POSTED]->(j1)
            
            CREATE (j2:Job {
                title: 'IT Support',
                description: 'Looking for an IT support specialist',
                requirements: 'Networking, Hardware, Customer Service',
                salary: '25000',
                job_type: 'Full Time',
                location: 'Virac',
                created_at: datetime()
            })
            CREATE (b)-[:POSTED]->(j2)
        """)

        # Create sample applications
        session.run("""
            MATCH (u:User {email: 'john@example.com'})
            MATCH (j:Job {title: 'Software Developer'})
            CREATE (a:Application {
                cover_letter: 'I am excited to apply for this position...',
                status: 'pending',
                created_at: datetime()
            })
            CREATE (u)-[:APPLIED_TO]->(a)
            CREATE (a)-[:FOR_JOB]->(j)
        """)

def main():
    print("Clearing database...")
    clear_database()
    print("Creating sample data...")
    create_sample_data()
    print("Done!")

if __name__ == "__main__":
    main() 