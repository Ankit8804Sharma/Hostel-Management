def _login_student(client, email='test@student.com', password='password123'):
    return client.post('/auth/login/student', data={'email': email, 'password': password}, follow_redirects=False)

def _login_staff(client, email, password='password123'):
    return client.post('/auth/login/staff', data={'email': email, 'password': password}, follow_redirects=False)


def test_student_dashboard_unauthenticated(client, db):
    response = client.get('/student/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_student_dashboard_authenticated(client, student_user):
    _login_student(client)
    response = client.get('/student/dashboard')
    assert response.status_code == 200


def test_student_dashboard_blocked_for_staff(client, warden_user):
    _login_staff(client, email='test@warden.com')
    response = client.get('/student/dashboard', follow_redirects=False)
    assert response.status_code == 302


def test_new_complaint_get(client, student_user):
    _login_student(client)
    response = client.get('/student/complaint/new')
    assert response.status_code == 200


def test_new_complaint_post_valid(client, student_user):
    _login_student(client)
    response = client.post('/student/complaint/new', data={
        'type': 'Electrical',
        'description': 'The fan is not working in room 101.'
    }, follow_redirects=False)
    assert response.status_code == 302


def test_new_complaint_post_invalid_type(client, student_user):
    _login_student(client)
    response = client.post('/student/complaint/new', data={
        'type': 'InvalidType',
        'description': 'Some description'
    }, follow_redirects=True)
    # Route flashes an error and redirects back to the form
    assert response.status_code == 200
    assert b'Please choose a category' in response.data


def test_complaints_list(client, student_user):
    _login_student(client)
    response = client.get('/student/complaints')
    assert response.status_code == 200


def test_student_profile_get(client, student_user):
    _login_student(client)
    response = client.get('/student/profile')
    assert response.status_code == 200
