import enum
from datetime import date, datetime, timezone

from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class RoomType(enum.Enum):
    AC = 'AC'
    NON_AC = 'Non-AC'


class AttendanceStatus(enum.Enum):
    PRESENT = 'Present'
    ABSENT = 'Absent'
    LEAVE = 'Leave'


class Hostel(db.Model):
    __tablename__ = 'hostel'
    hostel_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    no_of_rooms = db.Column(db.Integer, nullable=False)
    hostel_contact = db.Column(db.String(30), nullable=False)

    rooms = db.relationship('Room', back_populates='hostel', lazy='dynamic')
    wardens = db.relationship('Warden', back_populates='hostel', lazy='dynamic')


class Room(db.Model):
    """Parent room entity; AC_Room and Non_AC_Room are ISA subtypes (joined inheritance)."""
    __tablename__ = 'room'
    __table_args__ = (
        UniqueConstraint('hostel_id', 'room_no', name='uq_room_hostel_room_no'),
    )

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.hostel_id'), nullable=False)
    room_no = db.Column(db.String(50), nullable=False)
    room_type = db.Column(db.Enum(RoomType), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)

    hostel = db.relationship('Hostel', back_populates='rooms')
    allocations = db.relationship('RoomAllocation', back_populates='room', lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_identity': 'room',
        'polymorphic_on': type,
    }


class AC_Room(Room):
    __tablename__ = 'ac_room'
    id = db.Column(db.Integer, db.ForeignKey('room.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'ac_room'}


class Non_AC_Room(Room):
    __tablename__ = 'non_ac_room'
    id = db.Column(db.Integer, db.ForeignKey('room.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'non_ac_room'}


class StaffMember(UserMixin, db.Model):
    __tablename__ = 'staff_members'

    staff_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_no = db.Column(db.String(20), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # Valid roles: 'staff', 'warden', 'chief_warden', 'admin'
    role = db.Column(db.String(50), nullable=False)

    warden_profile = db.relationship('Warden', back_populates='staff', uselist=False)
    complaints_handled = db.relationship('Complaint', back_populates='staff', lazy='dynamic')
    tasks = db.relationship('TaskAllocation', back_populates='staff', lazy='dynamic')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return f'staff_{self.staff_id}'


class Warden(db.Model):
    __tablename__ = 'warden'

    warden_id = db.Column(db.Integer, primary_key=True)
    contact_no = db.Column(db.String(20), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.hostel_id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.staff_id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)

    hostel = db.relationship('Hostel', back_populates='wardens')
    staff = db.relationship('StaffMember', back_populates='warden_profile')

    __mapper_args__ = {
        'polymorphic_identity': 'warden',
        'polymorphic_on': type,
    }


class ChiefWarden(Warden):
    __tablename__ = 'chief_warden'
    warden_id = db.Column(db.Integer, db.ForeignKey('warden.warden_id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'chief_warden'}


class Student(UserMixin, db.Model):
    __tablename__ = 'student'

    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    roll_number = db.Column(db.String(50), nullable=True, unique=True)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    address = db.Column(db.Text, nullable=True)

    room_allocations = db.relationship('RoomAllocation', back_populates='student', lazy='dynamic')
    equipment_usages = db.relationship('EquipmentUsage', back_populates='student', lazy='dynamic')
    laundry_orders = db.relationship('Laundry', back_populates='student', lazy='dynamic')
    complaints = db.relationship('Complaint', back_populates='student', lazy='dynamic')
    attendance_records = db.relationship('Attendance', back_populates='student', lazy='dynamic')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return f'student_{self.student_id}'


class RoomAllocation(db.Model):
    __tablename__ = 'room_allocation'

    alloc_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    alloc_date = db.Column(db.Date, nullable=False)
    vacate_date = db.Column(db.Date, nullable=True)

    student = db.relationship('Student', back_populates='room_allocations')
    room = db.relationship('Room', back_populates='allocations')


class GamingFacilities(db.Model):
    __tablename__ = 'gaming_facilities'

    serial_no = db.Column(db.Integer, primary_key=True)
    equipment_name = db.Column(db.String(200), nullable=False)
    availability_status = db.Column(db.String(50), nullable=False)

    usages = db.relationship('EquipmentUsage', back_populates='equipment', lazy='dynamic')


class EquipmentUsage(db.Model):
    __tablename__ = 'equipment_usage'

    usage_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    serial_no = db.Column(db.Integer, db.ForeignKey('gaming_facilities.serial_no'), nullable=False)
    issued_time = db.Column(db.DateTime, nullable=False)
    submission_time = db.Column(db.DateTime, nullable=True)

    student = db.relationship('Student', back_populates='equipment_usages')
    equipment = db.relationship('GamingFacilities', back_populates='usages')


class Laundry(db.Model):
    __tablename__ = 'laundry'

    laundry_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    items = db.Column(db.Text, nullable=True)
    pickup_date = db.Column(db.Date, nullable=True)
    special_instructions = db.Column(db.String(500), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)

    student = db.relationship('Student', back_populates='laundry_orders')


class Complaint(db.Model):
    __tablename__ = 'complaint'

    complaint_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.staff_id', ondelete='SET NULL'), nullable=True)
    attachment_filename = db.Column(db.String(255), nullable=True)

    student = db.relationship('Student', back_populates='complaints')
    staff = db.relationship('StaffMember', back_populates='complaints_handled')
    feedback_entries = db.relationship('Feedback', back_populates='complaint', lazy='dynamic')


class Feedback(db.Model):
    """Weak entity: identified relative to Complaint."""
    __tablename__ = 'feedback'

    serial_no = db.Column(db.Integer, nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.complaint_id'), nullable=False)
    comments = db.Column(db.Text, nullable=False)

    complaint = db.relationship('Complaint', back_populates='feedback_entries')

    __table_args__ = (
        db.PrimaryKeyConstraint('complaint_id', 'serial_no'),
    )


class Attendance(db.Model):
    __tablename__ = 'attendance'

    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    status = db.Column(db.Enum(AttendanceStatus), nullable=False)

    student = db.relationship('Student', back_populates='attendance_records')


class TaskAllocation(db.Model):
    __tablename__ = 'task_allocation'

    task_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_members.staff_id'), nullable=False)
    assigned_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    notes = db.Column(db.Text, nullable=True)

    staff = db.relationship('StaffMember', back_populates='tasks')


class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'staff'
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
