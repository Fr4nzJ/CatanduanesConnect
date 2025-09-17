from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_db_connection():
    # Neo4j Configuration from environment variables
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session(database=database) as session:
            # Try to execute a simple query
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            if test_value == 1:
                print("✅ Database connection successful!")
                print(f"URI: {uri}")
                print(f"Database: {database}")
                return True
            else:
                print("❌ Database connection test failed!")
                return False
    except Exception as e:
        print("❌ Database connection error:")
        print(str(e))
        return False
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == '__main__':
    test_db_connection()