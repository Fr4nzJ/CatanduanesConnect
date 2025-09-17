import requests
import json
from datetime import datetime

BASE_URL = 'http://localhost:5000'
SESSION = requests.Session()

def print_test_result(test_name, passed):
    print(f"{'✓' if passed else '✗'} {test_name}: {'PASSED' if passed else 'FAILED'}")

def test_regular_signup():
    # Test regular user signup
    response = SESSION.post(f'{BASE_URL}/signup', data={
        'name': f'Test User {datetime.now().timestamp()}',
        'email': f'test{datetime.now().timestamp()}@example.com',
        'password': 'test123',
        'confirm_password': 'test123',
        'role': 'job_seeker'
    })
    success = 'dashboard' in response.url  # Should redirect to dashboard on success
    print_test_result('Regular User Signup', success)
    return success

def test_admin_login():
    # Test admin login
    response = SESSION.post(f'{BASE_URL}/login', data={
        'email': 'ermido09@gmail.com',
        'password': 'Fr4nzJermido'
    })
    success = 'dashboard' in response.url
    print_test_result('Admin Login', success)
    return success

def test_unauthorized_admin_access():
    # First, create and login as regular user
    test_regular_signup()
    
    # Try to access admin dashboard
    response = SESSION.get(f'{BASE_URL}/admin/dashboard')
    success = 'Unauthorized' in response.text or response.status_code in [302, 403]
    print_test_result('Unauthorized Admin Access Prevention', success)
    return success

def test_role_change_prevention():
    # Try to update user role to admin
    response = SESSION.post(f'{BASE_URL}/profile/edit', data={
        'name': 'Test User',
        'role': 'admin'  # This should be ignored
    })
    
    # Check if still regular user
    response = SESSION.get(f'{BASE_URL}/dashboard')
    success = 'admin' not in response.text.lower()
    print_test_result('Role Change Prevention', success)
    return success

def run_all_tests():
    print("\nRunning Security Tests...")
    print("-" * 50)
    
    results = []
    results.append(test_regular_signup())
    SESSION.get(f'{BASE_URL}/logout')  # Logout before next test
    
    results.append(test_admin_login())
    SESSION.get(f'{BASE_URL}/logout')
    
    results.append(test_unauthorized_admin_access())
    SESSION.get(f'{BASE_URL}/logout')
    
    results.append(test_role_change_prevention())
    
    print("-" * 50)
    print(f"Tests Passed: {sum(results)}/{len(results)}")
    
if __name__ == '__main__':
    run_all_tests()