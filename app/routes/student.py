from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Attendance, AttendanceStatus, Complaint, EquipmentUsage, GamingFacilities, Laundry, Student

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
        if not current_user.get_id().startswith('student_'):
            flash('This area is for students only.', 'error')
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
    )


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


@student_bp.route('/laundry/new', methods=['POST'])
@login_required
@student_only
def new_laundry():
    items = request.form.get('items', '').strip()
    weight_raw = request.form.get('weight', '')
    try:
        weight = float(weight_raw)
    except (TypeError, ValueError):
        flash('Please enter a valid weight.', 'error')
        return redirect(url_for('student.dashboard'))
    if weight <= 0:
        flash('Weight must be greater than zero.', 'error')
        return redirect(url_for('student.dashboard'))
    row = Laundry(
        date=date.today(),
        weight=weight,
        status='Pending',
        items=items or None,
        student_id=current_user.student_id,
    )
    db.session.add(row)
    db.session.commit()
    flash('Laundry request submitted.', 'success')
    return redirect(url_for('student.dashboard'))


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


@student_bp.route('/gaming/return/<int:usage_id>', methods=['POST'])
@login_required
@student_only
def gaming_return(usage_id):
    """Return gaming equipment."""
    from datetime import datetime
    usage = EquipmentUsage.query.get_or_404(usage_id)
    if usage.student_id != current_user.student_id:
        abort(403)
    if usage.submission_time is not None:
        flash('This equipment has already been returned.', 'info')
        return redirect(url_for('student.gaming'))
    usage.submission_time = datetime.now()
    if usage.equipment:
        usage.equipment.availability_status = 'Available'
    db.session.commit()
    flash('Equipment returned. Thanks!', 'success')
    return redirect(url_for('student.gaming'))
