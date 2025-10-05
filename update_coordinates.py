from neo4j import GraphDatabase
from database import driver, DATABASE, get_neo4j_driver

# Ensure we have a driver
if driver is None:
    driver = get_neo4j_driver()

def update_coordinates():
    with driver.session() as session:
        # Update businesses with default coordinates
        session.run("""
            MATCH (b:Business)
            WHERE b.latitude IS NULL OR b.longitude IS NULL
            SET b.latitude = 13.5, b.longitude = 124.3
        """)
        
        # Update jobs with their business coordinates
        session.run("""
            MATCH (j:Job)<-[:POSTED]-(b:Business)
            WHERE j.latitude IS NULL OR j.longitude IS NULL
            SET j.latitude = b.latitude, j.longitude = b.longitude
        """)
        
        # Update any remaining jobs with default coordinates
        session.run("""
            MATCH (j:Job)
            WHERE j.latitude IS NULL OR j.longitude IS NULL
            SET j.latitude = 13.5, j.longitude = 124.3
        """)

if __name__ == "__main__":
    try:
        update_coordinates()
        print("Successfully updated coordinates for all businesses and jobs.")
    except Exception as e:
        print(f"Error updating coordinates: {str(e)}")
    finally:
        driver.close() 