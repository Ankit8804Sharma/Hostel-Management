import pytest
from app import create_app, db as _db
from app.models import Student, StaffMember
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    _db.create_all()
    yield _db
    _db.session.remove()
    _db.drop_all()

@pytest.fixture
def student_user(db):
    student = Student(
        name='Test Student',
        email='test@student.com',
        phone_number='1234567890',
        password_hash=generate_password_hash('password123')
    )
    _db.session.add(student)
    _db.session.commit()
    return student

@pytest.fixture
def warden_user(db):
    warden = StaffMember(
        name='Test Warden',
        contact_no='0987654321',
        designation='Warden',
        email='test@warden.com',
        role='warden',
        password_hash=generate_password_hash('password123')
    )
    _db.session.add(warden)
    _db.session.commit()
    return warden

@pytest.fixture
def staff_user(db):
    staff = StaffMember(
        name='Test Staff',
        contact_no='1122334455',
        designation='Maintenance',
        email='staff@test.com',
        role='staff',
        password_hash=generate_password_hash('password123')
    )
    _db.session.add(staff)
    _db.session.commit()
    return staff
