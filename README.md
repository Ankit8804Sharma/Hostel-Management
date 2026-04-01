<h1 align="center">🏨 Hostel Complaint &amp; Maintenance Management System</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" />
</p>

<p align="center">
  A full-stack web application for managing hostel operations — complaints, maintenance tasks, laundry, attendance, and gaming facilities — across three user roles: <strong>Student</strong>, <strong>Warden</strong>, and <strong>Staff</strong>.
</p>

---

## 📋 Table of Contents

- [Description](#-description)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [Default Login Credentials](#-default-login-credentials)
- [Database Schema](#-database-schema)

---

## 📝 Description

The **Hostel Complaint &amp; Maintenance Management System** is a role-based web application built with Flask and MySQL. It streamlines day-to-day hostel management by providing dedicated dashboards for students, wardens, and maintenance staff.

Students can raise complaints, track laundry orders, and check their attendance. Wardens oversee all complaints, mark student attendance, and assign tasks to staff members. Staff members view their assigned tasks and update completion status — all within a clean, responsive Bootstrap 5 interface.

---

## ✨ Features

### 🎓 Student
- Submit complaints (Electrical, Plumbing, Internet, Cleanliness, Furniture, etc.)
- Track complaint status in real time (Open → In Progress → Resolved)
- Place and monitor laundry orders with item details and weight
- View available gaming facilities (PlayStation, Xbox, Chess, etc.)
- Check personal attendance records

### 🏛️ Warden
- View and manage all student complaints across the hostel
- Assign complaints to specific staff members
- Mark daily student attendance (Present / Absent / Leave)
- Create and assign maintenance tasks to staff

### 🔧 Staff
- View all tasks assigned by the warden
- Update task status (Pending → Completed)
- View complaints assigned for resolution

---

## 🛠 Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Language     | Python 3.10+                        |
| Framework    | Flask 3.0                           |
| Database     | MySQL 8.0                           |
| ORM          | Flask-SQLAlchemy + SQLAlchemy       |
| Migrations   | Flask-Migrate (Alembic)             |
| Auth         | Flask-Login + Werkzeug              |
| Frontend     | Bootstrap 5, Jinja2 Templates       |
| Environment  | python-dotenv                       |
| DB Driver    | PyMySQL                             |

---

## 📁 Project Structure

```
Hostel-Management/
│
├── app/                        # Main application package
│   ├── __init__.py             # App factory, extensions (db, login_manager)
│   ├── models.py               # SQLAlchemy models (Student, Staff, Room, etc.)
│   ├── routes/
│   │   ├── auth.py             # Login / logout for students & staff
│   │   ├── student.py          # Student dashboard & features
│   │   ├── warden.py           # Warden dashboard & management
│   │   └── staff.py            # Staff task & complaint views
│   ├── static/                 # CSS, JS, images
│   └── templates/              # Jinja2 HTML templates
│
├── migrations/                 # Flask-Migrate / Alembic migration files
│
├── .env                        # Environment variables (not committed)
├── config.py                   # App configuration (reads from .env)
├── run.py                      # Application entry point
├── seed.py                     # Database seeder with sample data
└── requirements.txt            # Python dependencies
```

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10+
- MySQL 8.0 running locally or remotely
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Ankit8804Sharma/Hostel-Management.git
cd Hostel-Management
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root (or update the existing one):

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://username:password@localhost/hostel_db
```

> **Note:** Create the `hostel_db` database in MySQL before running migrations:
> ```sql
> CREATE DATABASE hostel_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> ```

### 5. Run Database Migrations

```bash
python -m flask db upgrade
```

### 6. Seed the Database

```bash
python seed.py
```

This will populate the database with sample hostels, rooms, staff, students, complaints, laundry orders, tasks, and attendance records.

### 7. Run the Application

```bash
python run.py
```

Open your browser and navigate to: **http://127.0.0.1:5000**

---

## 🔑 Default Login Credentials

> These credentials are created automatically when you run `python seed.py`.

| Role    | Email                  | Password     |
|---------|------------------------|--------------|
| Student | ankit@student.com      | student123   |
| Student | priya@student.com      | student123   |
| Student | rahul@student.com      | student123   |
| Staff   | rajesh@hostel.com      | staff123     |
| Staff   | priya@hostel.com       | staff123     |
| Warden  | amit@hostel.com        | staff123     |

---

## 🗄️ Database Schema

The application uses a **joined-table inheritance** strategy for polymorphic entities:

- **Room** → `AC_Room` / `Non_AC_Room`
- **Warden** → `ChiefWarden`

**Core tables:**

| Table              | Description                                  |
|--------------------|----------------------------------------------|
| `hostel`           | Hostel blocks with type and room count       |
| `room`             | Parent room entity (polymorphic)             |
| `ac_room`          | AC room subtype                              |
| `non_ac_room`      | Non-AC room subtype                          |
| `staff_members`    | Staff and warden user accounts               |
| `warden`           | Warden ↔ hostel mapping                      |
| `student`          | Student user accounts                        |
| `room_allocation`  | Student ↔ room assignments                   |
| `complaint`        | Student complaints with staff assignment     |
| `feedback`         | Weak entity linked to complaints             |
| `laundry`          | Laundry orders per student                   |
| `gaming_facilities`| Available gaming equipment                   |
| `equipment_usage`  | Equipment issue/return log                   |
| `task_allocation`  | Maintenance tasks assigned to staff          |
| `attendance`       | Daily student attendance records             |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

<p align="center">Made with ❤️ using Flask &amp; MySQL</p>
