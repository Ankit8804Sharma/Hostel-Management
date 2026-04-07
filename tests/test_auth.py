import os

def test_student_register_success(client, db):
    response = client.post('/auth/register/student', data={
        'name': 'New Student',
        'email': 'new@student.com',
        'phone': '1234567890',
        'password': 'password123'
    })
    assert response.status_code == 302

def test_student_register_duplicate_email(client, db, student_user):
    response = client.post('/auth/register/student', data={
        'name': 'Another Student',
        'email': 'test@student.com',
        'phone': '0987654321',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert b'Email already registered.' in response.data

def test_student_login_success(client, student_user):
    response = client.post('/auth/login/student', data={
        'email': 'test@student.com',
        'password': 'password123'
    })
    assert response.status_code == 302

def test_student_login_wrong_password(client, student_user):
    response = client.post('/auth/login/student', data={
        'email': 'test@student.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200
    assert b'Invalid email or password.' in response.data

def test_staff_register_without_invite_code(client, db):
    response = client.post('/auth/register/staff', data={
        'name': 'New Staff',
        'email': 'new@staff.com',
        'contact_no': '1234567890',
        'designation': 'Staff',
        'password': 'password123'
    })
    assert response.status_code == 403

def test_staff_register_with_invite_code(client, db):
    invite_code = os.environ.get('STAFF_INVITE_CODE')
    response = client.post('/auth/register/staff', data={
        'invite_code': invite_code,
        'name': 'New Staff',
        'email': 'new@staff.com',
        'contact_no': '1234567890',
        'designation': 'Staff',
        'password': 'password123'
    })
    assert response.status_code == 302
