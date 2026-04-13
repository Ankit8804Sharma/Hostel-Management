# Hostel Management System

A full-stack web application for managing hostel operations including student registrations, room allocations, complaints, laundry, attendance, gaming equipment, and staff task management.

## Features

**Student**
- Register, login, edit profile
- Submit and track complaints with image attachments
- Book and return gaming equipment
- Place and track laundry orders
- View room allocation and attendance history
- In-app notifications and feedback on resolved complaints

**Warden**
- Dashboard with complaint charts and filters
- Assign complaints to staff, update status
- Mark attendance for all students
- Allocate and vacate student rooms
- Assign tasks to staff with priority and due dates
- Manage gaming equipment
- Laundry order status management
- Analytics overview with CSV export

**Staff**
- View assigned complaints and tasks
- Mark tasks complete, update complaint status

**Admin**
- Create and manage hostels and rooms

**Security**
- CSRF protection on all forms
- Rate limiting on login endpoints
- JWT-based REST API authentication
- Session cookie hardening
- Security response headers

## Tech Stack
Flask, SQLAlchemy, MySQL, Flask-Login, Flask-WTF, Flask-Mail, Flask-JWT-Extended, Flask-Limiter, Bootstrap 5, Chart.js

## Setup

```bash
git clone <repo-url>
cd Hostel-Management
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env         # fill in your values
flask db upgrade
python seed.py
flask run
```

## Environment Variables

| Variable | Description |
|---|---|
| SECRET_KEY | Flask session secret |
| DATABASE_URL | MySQL connection string |
| WTF_CSRF_SECRET_KEY | CSRF protection key |
| STAFF_INVITE_CODE | Required code to register as staff |
| JWT_SECRET_KEY | JWT signing secret |
| MAIL_* | SMTP mail settings |

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/v1/auth/login/student | None | Student login, returns JWT |
| POST | /api/v1/auth/login/staff | None | Staff login, returns JWT |
| GET | /api/v1/student/complaints | JWT | List student complaints |
| POST | /api/v1/student/complaints | JWT | Submit new complaint |
| GET | /api/v1/student/profile | JWT | Get student profile |
| GET | /api/v1/warden/complaints | JWT (warden) | List all complaints paginated |
| PATCH | /api/v1/warden/complaints/<id>/status | JWT (warden) | Update complaint status |

## Running Tests

```bash
pytest -v
```
