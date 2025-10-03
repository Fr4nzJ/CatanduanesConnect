from database import get_neo4j_driver

def check_database():
    driver = get_neo4j_driver()
    with driver.session() as session:
        print("Checking database contents...")
        
        # Check node counts
        result = session.run("""
            MATCH (n) 
            WITH labels(n) as labels, count(n) as count
            RETURN labels, count
        """)
        print("\nNode counts:")
        for record in result:
            print(f"{record['labels']}: {record['count']} nodes")
        
        # Check User nodes specifically
        result = session.run("""
            MATCH (u:User)
            RETURN u.role as role, count(u) as count
            ORDER BY role
        """)
        print("\nUser roles:")
        for record in result:
            print(f"Role '{record['role']}': {record['count']} users")
        
        # Check recent activities
        result = session.run("""
            MATCH (a:Activity)
            RETURN count(a) as count
        """)
        activity_count = result.single()['count']
        print(f"\nNumber of activities: {activity_count}")

if __name__ == "__main__":
    check_database()