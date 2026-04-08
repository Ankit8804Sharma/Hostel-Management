import json


def test_api_student_login_success(client, student_user):
    response = client.post('/api/v1/auth/login/student',
        data=json.dumps({'email': 'test@student.com', 'password': 'password123'}),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data


def test_api_student_login_wrong_password(client, student_user):
    response = client.post('/api/v1/auth/login/student',
        data=json.dumps({'email': 'test@student.com', 'password': 'wrongpassword'}),
        content_type='application/json'
    )
    assert response.status_code == 401


def test_api_complaints_without_token(client, db):
    response = client.get('/api/v1/student/complaints')
    assert response.status_code == 401


def test_api_complaints_with_token(client, student_user):
    # First login to get token
    login_resp = client.post('/api/v1/auth/login/student',
        data=json.dumps({'email': 'test@student.com', 'password': 'password123'}),
        content_type='application/json'
    )
    token = login_resp.get_json()['access_token']

    # Then use token to fetch complaints
    response = client.get('/api/v1/student/complaints',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_api_create_complaint(client, student_user):
    # Login to get token
    login_resp = client.post('/api/v1/auth/login/student',
        data=json.dumps({'email': 'test@student.com', 'password': 'password123'}),
        content_type='application/json'
    )
    token = login_resp.get_json()['access_token']

    # Create a complaint
    response = client.post('/api/v1/student/complaints',
        data=json.dumps({'complaint_type': 'Plumbing', 'description': 'Pipe is leaking in bathroom.'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
