from database import get_neo4j_driver, DATABASE

def check_user(email):
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        result = session.run(
            'MATCH (u:User {email: $email}) RETURN u.email, u.role, u.verification_status',
            email=email
        )
        record = result.single()
        if record:
            print(f'User Details:')
            print(f'Email: {record["u.email"]}')
            print(f'Role: {record["u.role"]}')
            print(f'Status: {record["u.verification_status"]}')
        else:
            print(f'No user found with email: {email}')

if __name__ == '__main__':
    check_user('murokamikentaro@gmail.com')