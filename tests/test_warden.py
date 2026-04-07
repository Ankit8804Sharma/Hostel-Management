def test_warden_dashboard_unauthenticated(client):
    response = client.get('/warden/dashboard')
    assert response.status_code == 302

def test_warden_dashboard_as_student(client, student_user):
    client.post('/auth/login/student', data={
        'email': 'test@student.com',
        'password': 'password123'
    })
    response = client.get('/warden/dashboard')
    assert response.status_code == 302

def test_warden_dashboard_as_warden(client, warden_user):
    client.post('/auth/login/staff', data={
        'email': 'test@warden.com',
        'password': 'password123'
    })
    response = client.get('/warden/dashboard')
    assert response.status_code == 200
