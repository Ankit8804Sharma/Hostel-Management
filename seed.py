"""
seed.py – Populate the Hostel Management database with sample data.

Run directly:
    python seed.py

Or import and call seed_db() inside an existing app context.
"""

from datetime import date

from app import db
from app.models import (
    AC_Room,
    Attendance,
    AttendanceStatus,
    Complaint,
    GamingFacilities,
    Hostel,
    Laundry,
    Non_AC_Room,
    RoomType,
    StaffMember,
    Student,
    TaskAllocation,
    Warden,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_or_none(model, **kwargs):
    """Return the first matching record or None."""
    return model.query.filter_by(**kwargs).first()


# ---------------------------------------------------------------------------
# Individual seeders
# ---------------------------------------------------------------------------

def _seed_hostels():
    hostels_data = [
        dict(name="Block A Hostel", type="Boys",  no_of_rooms=50, hostel_contact="9876543201"),
        dict(name="Block B Hostel", type="Girls", no_of_rooms=40, hostel_contact="9876543202"),
    ]

    created = {}
    for data in hostels_data:
        existing = Hostel.query.filter_by(hostel_contact=data["hostel_contact"]).first()
        if existing:
            print(f"  [SKIP] Hostel '{data['name']}' already exists.")
            created[data["name"]] = existing
        else:
            hostel = Hostel(
                type=data["type"],
                no_of_rooms=data["no_of_rooms"],
                hostel_contact=data["hostel_contact"],
            )
            db.session.add(hostel)
            db.session.flush()  # get hostel_id without committing
            created[data["name"]] = hostel
            print(f"  [ADD]  Hostel '{data['name']}' created.")
    return created


def _seed_rooms(hostels):
    block_a = hostels["Block A Hostel"]

    rooms_data = [
        # AC rooms
        dict(room_no="101", room_type=RoomType.AC,     capacity=2, cls=AC_Room),
        dict(room_no="102", room_type=RoomType.AC,     capacity=2, cls=AC_Room),
        dict(room_no="103", room_type=RoomType.AC,     capacity=2, cls=AC_Room),
        # Non-AC rooms
        dict(room_no="201", room_type=RoomType.NON_AC, capacity=4, cls=Non_AC_Room),
        dict(room_no="202", room_type=RoomType.NON_AC, capacity=4, cls=Non_AC_Room),
        dict(room_no="203", room_type=RoomType.NON_AC, capacity=4, cls=Non_AC_Room),
    ]

    created = {}
    for data in rooms_data:
        from sqlalchemy import and_
        existing = (
            data["cls"]
            .query.filter(
                data["cls"].hostel_id == block_a.hostel_id,
                data["cls"].room_no == data["room_no"],
            )
            .first()
        )
        if existing:
            print(f"  [SKIP] Room {data['room_no']} already exists.")
            created[data["room_no"]] = existing
        else:
            room = data["cls"](
                hostel_id=block_a.hostel_id,
                room_no=data["room_no"],
                room_type=data["room_type"],
                capacity=data["capacity"],
            )
            db.session.add(room)
            db.session.flush()
            created[data["room_no"]] = room
            print(f"  [ADD]  Room {data['room_no']} ({data['room_type'].value}) created.")
    return created


def _seed_staff():
    staff_data = [
        dict(
            name="Rajesh Kumar",
            email="rajesh@hostel.com",
            password="staff123",
            contact_no="9000000001",
            designation="Maintenance",
            role="staff",
        ),
        dict(
            name="Priya Sharma",
            email="priya@hostel.com",
            password="staff123",
            contact_no="9000000002",
            designation="Cleanliness",
            role="staff",
        ),
        dict(
            name="Amit Singh",
            email="amit@hostel.com",
            password="staff123",
            contact_no="9000000003",
            designation="Warden",
            role="warden",
        ),
    ]

    created = {}
    for data in staff_data:
        existing = StaffMember.query.filter_by(email=data["email"]).first()
        if existing:
            print(f"  [SKIP] Staff '{data['name']}' already exists.")
            created[data["name"]] = existing
        else:
            member = StaffMember(
                name=data["name"],
                email=data["email"],
                contact_no=data["contact_no"],
                designation=data["designation"],
                role=data["role"],
            )
            member.set_password(data["password"])
            db.session.add(member)
            db.session.flush()
            created[data["name"]] = member
            print(f"  [ADD]  Staff '{data['name']}' created.")
    return created


def _seed_warden(hostels, staff):
    block_a = hostels["Block A Hostel"]
    amit = staff["Amit Singh"]

    existing = Warden.query.filter_by(staff_id=amit.staff_id).first()
    if existing:
        print("  [SKIP] Warden entry for Amit Singh already exists.")
        return existing

    warden = Warden(
        name=amit.name,
        email=amit.email,
        contact_no=amit.contact_no,
        hostel_id=block_a.hostel_id,
        staff_id=amit.staff_id,
        type="warden",
    )
    db.session.add(warden)
    db.session.flush()
    print("  [ADD]  Warden entry for Amit Singh created.")
    return warden


def _seed_students():
    students_data = [
        dict(name="Ankit Sharma", email="ankit@student.com",  password="student123", phone_number="9876500001"),
        dict(name="Priya Patel",  email="priya@student.com",  password="student123", phone_number="9876500002"),
        dict(name="Rahul Verma",  email="rahul@student.com",  password="student123", phone_number="9876500003"),
        dict(name="Sneha Gupta",  email="sneha@student.com",  password="student123", phone_number="9876500004"),
        dict(name="Vikram Joshi", email="vikram@student.com", password="student123", phone_number="9876500005"),
    ]

    created = {}
    for data in students_data:
        existing = Student.query.filter_by(email=data["email"]).first()
        if existing:
            print(f"  [SKIP] Student '{data['name']}' already exists.")
            created[data["name"]] = existing
        else:
            student = Student(
                name=data["name"],
                email=data["email"],
                phone_number=data["phone_number"],
            )
            student.set_password(data["password"])
            db.session.add(student)
            db.session.flush()
            created[data["name"]] = student
            print(f"  [ADD]  Student '{data['name']}' created.")
    return created


def _seed_gaming_facilities():
    equipment_data = [
        "PlayStation 5",
        "Xbox Series X",
        "Chess Board",
    ]

    created = {}
    for name in equipment_data:
        existing = GamingFacilities.query.filter_by(equipment_name=name).first()
        if existing:
            print(f"  [SKIP] Gaming facility '{name}' already exists.")
            created[name] = existing
        else:
            facility = GamingFacilities(
                equipment_name=name,
                availability_status="Available",
            )
            db.session.add(facility)
            db.session.flush()
            created[name] = facility
            print(f"  [ADD]  Gaming facility '{name}' created.")
    return created


def _seed_complaints(students, staff):
    today = date.today()
    rajesh = staff["Rajesh Kumar"]
    priya_s = staff["Priya Sharma"]

    complaints_data = [
        dict(
            student=students["Ankit Sharma"],
            type="Electrical",
            description="Fan not working in room 101",
            status="Open",
            staff=None,
        ),
        dict(
            student=students["Priya Patel"],
            type="Plumbing",
            description="Tap leaking in bathroom",
            status="In Progress",
            staff=rajesh,
        ),
        dict(
            student=students["Rahul Verma"],
            type="Internet",
            description="WiFi not working since 2 days",
            status="Resolved",
            staff=priya_s,
        ),
        dict(
            student=students["Sneha Gupta"],
            type="Cleanliness",
            description="Room not cleaned for 3 days",
            status="Open",
            staff=None,
        ),
        dict(
            student=students["Vikram Joshi"],
            type="Furniture",
            description="Chair broken in room",
            status="In Progress",
            staff=rajesh,
        ),
    ]

    created = []
    for data in complaints_data:
        existing = Complaint.query.filter_by(
            student_id=data["student"].student_id,
            type=data["type"],
            description=data["description"],
        ).first()
        if existing:
            print(f"  [SKIP] Complaint '{data['type']}' for {data['student'].name} already exists.")
            created.append(existing)
        else:
            complaint = Complaint(
                type=data["type"],
                description=data["description"],
                status=data["status"],
                issue_date=today,
                student_id=data["student"].student_id,
                staff_id=data["staff"].staff_id if data["staff"] else None,
            )
            db.session.add(complaint)
            db.session.flush()
            created.append(complaint)
            print(f"  [ADD]  Complaint '{data['type']}' for {data['student'].name} created.")
    return created


def _seed_laundry(students):
    today = date.today()

    laundry_data = [
        dict(student=students["Ankit Sharma"], weight=2.5, items="Shirts, Jeans",            status="Pending"),
        dict(student=students["Priya Patel"],  weight=1.8, items="Kurtas, Dupattas",          status="Delivered"),
        dict(student=students["Rahul Verma"],  weight=3.0, items="Bedsheets, Pillow covers",  status="In Progress"),
        dict(student=students["Sneha Gupta"],  weight=2.0, items="Tops, Trousers",            status="Pending"),
    ]

    for data in laundry_data:
        existing = Laundry.query.filter_by(
            student_id=data["student"].student_id,
            items=data["items"],
        ).first()
        if existing:
            print(f"  [SKIP] Laundry entry for {data['student'].name} ({data['items']}) already exists.")
        else:
            order = Laundry(
                date=today,
                weight=data["weight"],
                status=data["status"],
                items=data["items"],
                student_id=data["student"].student_id,
            )
            db.session.add(order)
            print(f"  [ADD]  Laundry entry for {data['student'].name} created.")


def _seed_task_allocations(staff):
    rajesh  = staff["Rajesh Kumar"]
    priya_s = staff["Priya Sharma"]
    today   = date.today()

    tasks_data = [
        dict(description="Fix electrical wiring in Block A",  staff=rajesh,  status="Pending",   completed_date=None),
        dict(description="Clean common areas daily",          staff=priya_s, status="Completed",  completed_date=today),
        dict(description="Check plumbing in bathrooms",       staff=rajesh,  status="Pending",    completed_date=None),
    ]

    for data in tasks_data:
        existing = TaskAllocation.query.filter_by(
            description=data["description"],
            staff_id=data["staff"].staff_id,
        ).first()
        if existing:
            print(f"  [SKIP] Task '{data['description'][:40]}...' already exists.")
        else:
            task = TaskAllocation(
                description=data["description"],
                staff_id=data["staff"].staff_id,
                assigned_date=today,
                completed_date=data["completed_date"],
                status=data["status"],
            )
            db.session.add(task)
            print(f"  [ADD]  Task '{data['description'][:40]}' created.")


def _seed_attendance(students):
    today = date.today()

    attendance_data = [
        dict(student=students["Ankit Sharma"], status=AttendanceStatus.PRESENT),
        dict(student=students["Priya Patel"],  status=AttendanceStatus.PRESENT),
        dict(student=students["Rahul Verma"],  status=AttendanceStatus.ABSENT),
        dict(student=students["Sneha Gupta"],  status=AttendanceStatus.LEAVE),
        dict(student=students["Vikram Joshi"], status=AttendanceStatus.PRESENT),
    ]

    for data in attendance_data:
        existing = Attendance.query.filter_by(
            student_id=data["student"].student_id,
            date=today,
        ).first()
        if existing:
            print(f"  [SKIP] Attendance for {data['student'].name} on {today} already exists.")
        else:
            record = Attendance(
                student_id=data["student"].student_id,
                date=today,
                status=data["status"],
            )
            db.session.add(record)
            print(f"  [ADD]  Attendance for {data['student'].name}: {data['status'].value}.")


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def seed_db():
    print("\n=== Seeding Hostels ===")
    hostels = _seed_hostels()

    print("\n=== Seeding Rooms ===")
    _seed_rooms(hostels)

    print("\n=== Seeding Staff Members ===")
    staff = _seed_staff()

    print("\n=== Seeding Warden ===")
    _seed_warden(hostels, staff)

    print("\n=== Seeding Students ===")
    students = _seed_students()

    print("\n=== Seeding Gaming Facilities ===")
    _seed_gaming_facilities()

    print("\n=== Seeding Complaints ===")
    _seed_complaints(students, staff)

    print("\n=== Seeding Laundry ===")
    _seed_laundry(students)

    print("\n=== Seeding Task Allocations ===")
    _seed_task_allocations(staff)

    print("\n=== Seeding Attendance ===")
    _seed_attendance(students)

    db.session.commit()
    print("\n✅  All seed data committed successfully.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_db()
        print("Database seeded successfully!")
