def _login_student(client, email='test@student.com', password='password123'):
    return client.post('/auth/login/student', data={'email': email, 'password': password}, follow_redirects=False)

def _login_staff(client, email, password='password123'):
    return client.post('/auth/login/staff', data={'email': email, 'password': password}, follow_redirects=False)


def test_staff_dashboard_unauthenticated(client, db):
    response = client.get('/staff/dashboard', follow_redirects=False)
    assert response.status_code == 302


def test_staff_dashboard_as_student(client, student_user):
    _login_student(client)
    response = client.get('/staff/dashboard', follow_redirects=False)
    assert response.status_code == 302


def test_staff_dashboard_as_staff(client, staff_user):
    _login_staff(client, email='staff@test.com')
    response = client.get('/staff/dashboard')
    assert response.status_code == 200
