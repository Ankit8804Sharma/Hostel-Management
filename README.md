<h1 align="center">🏨 Hostel Complaint &amp; Maintenance Management System</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" />
</p>

<p align="center">
  <strong>A professional, full-stack management solution for modern hostels.</strong><br>
  Built with Flask, MySQL, and rich Bootstrap 5 aesthetics.
</p>

---

## 📋 Table of Contents
- [✨ Key Features](#-key-features)
- [🖥️ System Screenshots](#️-system-screenshots)
- [🛠️ Tech Stack](#️-tech-stack)
- [📡 API Reference](#-api-reference)
- [🗄️ Database Schema](#️-database-schema)
- [⚙️ Setup & Installation](#️-setup--installation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Key Features

### 🎓 For Students
- **Smart Dashboard**: Unified view of attendance, pending laundry, and available gaming facilities.
- **Activity Timeline**: A real-time chronological log of all recent interactions (complaints, laundry, gaming).
- **Maintenance Portal**: Raise complaints across 6+ categories with real-time **Visual Tracking**.
- **Facility Booking**: Real-time availability check and booking for gaming equipment (PS5, Xbox, Chess).
- **Laundry Management**: Place orders by weight and track progress from 'Pending' to 'Done'.
- **Room Details**: Transparent view of allocated room type, capacity, and hostel contact info.

### 🏛️ For Wardens (Admin)
- **Analytics Overview**: High-level data visualizations for complaint trends, room occupancy, and staff efficiency.
- **Filtered Management**: Advanced search and filter suite for complaints (by student, status, and type).
- **Staff Performance**: Scorecard system tracking task completion rates per staff member.
- **Student Database**: Searchable directory of all student allocations and contact details.
- **Reporting**: One-click **CSV Export** for complaints and professional **Printable Attendance Reports**.
- **Task Orchestration**: Assign specific complaints to staff and create independent maintenance tasks.

### 🔧 For Maintenance Staff
- **Personalized Worklist**: Clear view of assigned complaints and general maintenance tasks.
- **One-Click Updates**: Swiftly update task status once maintenance is completed.

---

## 🖥️ System Screenshots
| Student Dashboard | Warden Dashboard | Staff Dashboard |
| :---: | :---: | :---: |
| [Screenshot: Student Dashboard] | [Screenshot: Warden Dashboard] | [Screenshot: Staff Dashboard] |

---

## 🛠️ Tech Stack
- **Backend**: Python 3.10+, Flask 3.0
- **Database**: MySQL 8.0 (Relational)
- **ORM**: SQLAlchemy (Joined-table Inheritance)
- **Frontend**: Bootstrap 5, Chart.js, HTML5/CSS3, Jinja2
- **Auth**: Flask-Login, Werkzeug Security (Bcrypt)
- **Utilities**: Flask-Migrate, python-dotenv, PyMySQL

---

## 📡 API Reference

### Authentication
| Method | Route | Description |
| :--- | :--- | :--- |
| `GET/POST` | `/auth/login_student` | Student portal entry |
| `GET/POST` | `/auth/login_staff` | Staff/Warden admin entry |
| `GET/POST` | `/auth/register_student` | Student signup |
| `GET/POST` | `/auth/register_staff` | Staff/Warden signup |
| `GET` | `/auth/logout` | Terminate session |

### Student Portal
| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/student/dashboard` | Main student dashboard & activity log |
| `GET/POST` | `/student/complaint/new` | Raise a maintenance request |
| `GET` | `/student/complaint/<id>/feedback` | Provide feedback on resolved issues |
| `GET` | `/student/complaint/<id>/track` | Visual tracking of complaint lifecycle |
| `GET` | `/student/room` | Allocated room and hostel details |
| `POST` | `/student/gaming/book` | Reserve gaming equipment |

### Warden (Admin) Portal
| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/warden/overview` | Advanced analytics and performance charts |
| `GET` | `/warden/students` | Searchable student allocation database |
| `GET` | `/warden/complaints/export` | Download all complaints as CSV |
| `GET` | `/warden/attendance` | Mark and view daily attendance |
| `POST` | `/warden/complaint/<id>/update` | Assign staff or update complaint status |

---

## 🗄️ Database Schema
The application utilizes a **Polymorphic Joined-Table Inheritance** strategy for cleaner abstraction:
- **Users**: Split into `Student` and `StaffMember` (Warden is a specialization of Staff).
- **Rooms**: Parent `Room` entity with specialized `AC_Room` and `Non_AC_Room` subtypes.
- **Operations**: `Complaint` links Students to Staff; `TaskAllocation` tracks Warden-assigned staff work.

---

## ⚙️ Setup & Installation

### 1. Environment Setup
```bash
git clone https://github.com/Ankit8804Sharma/Hostel-Management.git
cd Hostel-Management
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root:
```env
FLASK_ENV=development
SECRET_KEY=your_secure_password
DATABASE_URL=mysql+pymysql://user:pass@localhost/hostel_db
```

### 3. Database Initialization
```bash
# In MySQL
CREATE DATABASE hostel_db;

# In Terminal
flask db upgrade
python seed.py
```

---

## 🤝 Contributing
Contributions are welcome! Please follow these steps:
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for more information.

---
<p align="center">Made with ❤️ for modern hostel living.</p>
