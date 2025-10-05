import os
from dotenv import load_dotenv
from database import driver, DATABASE, get_neo4j_driver

# Load environment variables
load_dotenv()

def test_db_connection():
    global driver
    # Ensure we have a driver
    if driver is None:
        driver = get_neo4j_driver()

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