from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import (
    Attendance,
    AttendanceStatus,
    Complaint,
    EquipmentUsage,
    GamingFacilities,
    Laundry,
    Room,
    RoomAllocation,
    StaffMember,
    Student,
)
from sqlalchemy.orm import joinedload

COMPLAINT_CATEGORIES = frozenset(
    {
        'Electrical',
        'Plumbing',
        'Cleanliness',
        'Furniture',
        'Internet',
        'Other',
    }
)

student_bp = Blueprint('student', __name__)


def student_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_student', next=request.url))
        if not isinstance(current_user, Student):
            flash('Access denied. This area is for students only.', 'danger')
            if isinstance(current_user, StaffMember):
                if current_user.role in ('warden', 'chief_warden'):
                    return redirect(url_for('warden.dashboard'))
                elif current_user.role == 'staff':
                    return redirect(url_for('staff.dashboard'))
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@student_bp.route('/dashboard')
@login_required
@student_only
def dashboard():
    student = Student.query.get_or_404(current_user.student_id)
    complaints = (
        Complaint.query.filter_by(student_id=student.student_id)
        .order_by(Complaint.issue_date.desc())
        .all()
    )
    laundry_orders = (
        Laundry.query.filter_by(student_id=student.student_id)
        .order_by(Laundry.date.desc())
        .all()
    )
    attendance = (
        Attendance.query.filter_by(student_id=student.student_id)
        .order_by(Attendance.date.desc())
        .limit(30)
        .all()
    )

    # Summary data
    total_complaints = len(complaints)
    pending_laundry_count = sum(1 for l in laundry_orders if l.status == 'Pending')
    available_gaming_count = GamingFacilities.query.filter_by(availability_status='Available').count()
    today_attendance = Attendance.query.filter_by(
        student_id=student.student_id,
        date=date.today()
    ).first()

    total_present = sum(1 for a in attendance if a.status == AttendanceStatus.PRESENT)
    total_absent  = sum(1 for a in attendance if a.status == AttendanceStatus.ABSENT)
    total_leave   = sum(1 for a in attendance if a.status == AttendanceStatus.LEAVE)

    # Combined activity log (Top 5)
    activities = []
    for c in complaints[:5]:
        activities.append({
            'type': 'complaint',
            'date': c.issue_date,
            'desc': f"Submitted {c.type} complaint",
            'status': c.status,
            'icon': 'bi-chat-left-text',
            'cls': 'text-primary'
        })
    for l in laundry_orders[:5]:
        activities.append({
            'type': 'laundry',
            'date': l.date,
            'desc': f"Laundry order ({l.weight}kg)",
            'status': l.status,
            'icon': 'bi-basket',
            'cls': 'text-success'
        })
    
    usages = EquipmentUsage.query.filter_by(student_id=student.student_id).order_by(EquipmentUsage.issued_time.desc()).limit(5).all()
    for u in usages:
        activities.append({
            'type': 'gaming',
            'date': u.issued_time.date(),
            'desc': f"Borrowed {u.equipment.equipment_name}",
            'status': 'Returned' if u.submission_time else 'Issued',
            'icon': 'bi-controller',
            'cls': 'text-info'
        })
    
    activities.sort(key=lambda x: x['date'], reverse=True)
    recent_activities = activities[:5]

    return render_template(
        'student/dashboard.html',
        student=student,
        complaints=complaints,
        laundry_orders=laundry_orders,
        attendance=attendance,
        total_complaints=total_complaints,
        pending_laundry_count=pending_laundry_count,
        available_gaming_count=available_gaming_count,
        today_attendance=today_attendance,
        total_present=total_present,
        total_absent=total_absent,
        total_leave=total_leave,
        complaint_categories=sorted(COMPLAINT_CATEGORIES),
        recent_activities=recent_activities,
    )


@student_bp.route('/room')
@login_required
@student_only
def room():
    """View student's current room allocation."""
    alloc = RoomAllocation.query.filter_by(
        student_id=current_user.student_id, 
        vacate_date=None
    ).options(joinedload(RoomAllocation.room).joinedload(Room.hostel)).first()
    return render_template('student/room.html', allocation=alloc)


@student_bp.route('/complaint/new', methods=['GET', 'POST'])
@login_required
@student_only
def new_complaint():
    """Submit a house complaint."""
    if request.method == 'POST':
        complaint_type = request.form.get('type', '').strip()
        description = request.form.get('description', '').strip()
        if complaint_type not in COMPLAINT_CATEGORIES or not description:
            flash('Please choose a category and enter a description.', 'error')
            return redirect(url_for('student.new_complaint'))
        row = Complaint(
            type=complaint_type,
            description=description,
            status='Open',
            issue_date=date.today(),
            student_id=current_user.student_id,
        )
        db.session.add(row)
        db.session.commit()
        flash('Your complaint was submitted successfully.', 'success')
        return redirect(url_for('student.dashboard'))

    # GET: show form
    return render_template(
        'student/new_complaint.html',
        complaint_categories=sorted(COMPLAINT_CATEGORIES),
    )


@student_bp.route('/laundry/new', methods=['GET', 'POST'])
@login_required
@student_only
def new_laundry():
    """Submit a laundry request."""
    if request.method == 'POST':
        items = request.form.get('items', '').strip()
        weight_raw = request.form.get('weight', '')
        try:
            weight = float(weight_raw)
        except (TypeError, ValueError):
            flash('Please enter a valid weight.', 'error')
            return redirect(url_for('student.new_laundry'))
        if weight <= 0:
            flash('Weight must be greater than zero.', 'error')
            return redirect(url_for('student.new_laundry'))
        row = Laundry(
            date=date.today(),
            weight=weight,
            status='Pending',
            items=items or None,
            student_id=current_user.student_id,
        )
        db.session.add(row)
        db.session.commit()
        flash('Laundry request submitted successfully.', 'success')
        return redirect(url_for('student.dashboard'))

    # GET: show form
    return render_template('student/new_laundry.html')


@student_bp.route('/gaming')
@login_required
@student_only
def gaming():
    """Show all gaming equipment with availability."""
    equipment_list = GamingFacilities.query.order_by(GamingFacilities.equipment_name).all()
    # Active usage for current student (not yet returned)
    active_usages = (
        EquipmentUsage.query
        .filter_by(student_id=current_user.student_id)
        .filter(EquipmentUsage.submission_time.is_(None))
        .all()
    )
    active_serials = {u.serial_no for u in active_usages}
    active_usage_map = {u.serial_no: u for u in active_usages}
    return render_template(
        'student/gaming.html',
        equipment_list=equipment_list,
        active_serials=active_serials,
        active_usage_map=active_usage_map,
    )


@student_bp.route('/gaming/book/<int:serial_no>', methods=['POST'])
@login_required
@student_only
def gaming_book(serial_no):
    """Issue gaming equipment to student."""
    from datetime import datetime
    equipment = GamingFacilities.query.get_or_404(serial_no)
    if equipment.availability_status != 'Available':
        flash('This equipment is not available right now.', 'error')
        return redirect(url_for('student.gaming'))
    # Check if student already has a pending usage for this item
    existing = EquipmentUsage.query.filter_by(
        student_id=current_user.student_id,
        serial_no=serial_no,
    ).filter(EquipmentUsage.submission_time.is_(None)).first()
    if existing:
        flash('You already have this equipment booked.', 'error')
        return redirect(url_for('student.gaming'))
    usage = EquipmentUsage(
        student_id=current_user.student_id,
        serial_no=serial_no,
        issued_time=datetime.now(),
    )
    equipment.availability_status = 'In Use'
    db.session.add(usage)
    db.session.commit()
    flash(f'\u201c{equipment.equipment_name}\u201d booked successfully!', 'success')
    return redirect(url_for('student.gaming'))


@student_bp.route('/gaming/return/<int:serial_no>', methods=['POST'])
@login_required
@student_only
def gaming_return(serial_no):
    """Return gaming equipment."""
    from datetime import datetime
    usage = (
        EquipmentUsage.query.filter_by(
            student_id=current_user.student_id,
            serial_no=serial_no,
            submission_time=None,
        )
        .first_or_404()
    )
    usage.submission_time = datetime.now()
    if usage.equipment:
        usage.equipment.availability_status = 'Available'
    db.session.commit()
    flash('Equipment returned successfully.', 'success')
    return redirect(url_for('student.gaming'))
@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_only
def profile():
    """View and update student profile."""
    student = Student.query.get_or_404(current_user.student_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone_number', '').strip()
        if not name or not phone:
            flash('Name and phone number are required.', 'error')
            return redirect(url_for('student.profile'))
        student.name = name
        student.phone_number = phone
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))

    # Statistics for the student
    stats = {
        'complaints': Complaint.query.filter_by(student_id=student.student_id).count(),
        'laundry': Laundry.query.filter_by(student_id=student.student_id).count(),
        'gaming': EquipmentUsage.query.filter_by(student_id=student.student_id).count(),
    }
    return render_template('student/profile.html', student=student, stats=stats)
@student_bp.route('/complaints')
@login_required
@student_only
def complaints_history():
    """View all complaints submitted by the student."""
    student = Student.query.get_or_404(current_user.student_id)
    complaints = (
        Complaint.query.filter_by(student_id=student.student_id)
        .order_by(Complaint.issue_date.desc())
        .all()
    )
    return render_template('student/complaints.html', student=student, complaints=complaints)


@student_bp.route('/laundry')
@login_required
@student_only
def laundry_history():
    """View all laundry orders submitted by the student."""
    student = Student.query.get_or_404(current_user.student_id)
    laundry_orders = (
        Laundry.query.filter_by(student_id=student.student_id)
        .order_by(Laundry.date.desc())
        .all()
    )
    return render_template('student/laundry.html', student=student, laundry_orders=laundry_orders)


@student_bp.route('/complaint/<int:complaint_id>/feedback', methods=['GET', 'POST'])
@login_required
@student_only
def complaint_feedback(complaint_id):
    """Submit feedback for a resolved complaint."""
    from app.models import Feedback
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Ensure complaint belongs to student and is resolved
    if complaint.student_id != current_user.student_id:
        flash('You can only give feedback for your own complaints.', 'error')
        return redirect(url_for('student.dashboard'))
    if complaint.status != 'Resolved':
        flash('Feedback can only be provided for resolved complaints.', 'error')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        comments = request.form.get('comments', '').strip()
        if not comments:
            flash('Please enter your feedback comments.', 'error')
            return redirect(url_for('student.complaint_feedback', complaint_id=complaint_id))
        
        # Calculate serial_no (weak entity relative to Complaint)
        from sqlalchemy import func
        max_serial = db.session.query(func.max(Feedback.serial_no)).filter_by(complaint_id=complaint_id).scalar() or 0
        
        feedback = Feedback(
            complaint_id=complaint_id,
            serial_no=max_serial + 1,
            comments=comments,
        )
        db.session.add(feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/complaint_feedback.html', complaint=complaint)


@student_bp.route('/complaint/<int:complaint_id>/track')
@login_required
@student_only
def track_complaint(complaint_id):
    """View the tracking timeline for a specific complaint."""
    complaint = Complaint.query.options(joinedload(Complaint.student), joinedload(Complaint.staff)).get_or_404(complaint_id)
    if complaint.student_id != current_user.student_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/complaint_track.html', complaint=complaint)
