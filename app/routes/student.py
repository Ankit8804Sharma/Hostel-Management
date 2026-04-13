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

from app.utils.email import send_complaint_received
from app.utils.uploads import save_complaint_attachment
from app.utils.notify import notify_student
from app.models import Notification

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
    student = db.get_or_404(Student, current_user.student_id)
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
        attachment_filename = save_complaint_attachment(request.files.get('attachment'))
        row = Complaint(
            type=complaint_type,
            description=description,
            status='Open',
            issue_date=date.today(),
            student_id=current_user.student_id,
            attachment_filename=attachment_filename,
        )
        db.session.add(row)
        db.session.commit()
        send_complaint_received(current_user.email, current_user.name, row.complaint_id, row.type)
        notify_student(current_user.student_id, f"Your complaint #{row.complaint_id} has been submitted.")
        flash('Your complaint was submitted successfully.', 'success')
        return redirect(url_for('student.dashboard'))

    # GET: show form
    return render_template(
        'student/new_complaint.html',
        complaint_categories=sorted(COMPLAINT_CATEGORIES),
    )


@student_bp.route('/notifications')
@login_required
@student_only
def notifications():
    """View and clear unread notifications."""
    notifs = Notification.query.filter_by(
        user_type='student', 
        user_id=current_user.student_id
    ).order_by(Notification.created_at.desc()).all()
    
    # Mark as read
    unread = [n for n in notifs if not n.is_read]
    if unread:
        for n in unread:
            n.is_read = True
        db.session.commit()
        
    return render_template('student/notifications.html', notifications=notifs)





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
    equipment = db.get_or_404(GamingFacilities, serial_no)
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

@student_bp.route('/complaints')
@login_required
@student_only
def complaints_history():
    """View all complaints submitted by the student."""
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')
    page = request.args.get('page', 1, type=int)

    query = Complaint.query.filter_by(student_id=current_user.student_id)
    if status_filter != 'All':
        query = query.filter(Complaint.status == status_filter)
    if type_filter != 'All':
        query = query.filter(Complaint.type == type_filter)
    if search:
        query = query.filter(Complaint.description.ilike(f'%{search}%'))

    complaints = query.order_by(Complaint.issue_date.desc()).paginate(page=page, per_page=10, error_out=False)
    COMPLAINT_STATUSES = ['Open', 'In Progress', 'Resolved']
    
    return render_template('student/complaints.html', 
                          complaints=complaints,
                          filters={'search': search, 'status': status_filter, 'type': type_filter},
                          COMPLAINT_CATEGORIES=sorted(list(COMPLAINT_CATEGORIES)),
                          complaint_statuses=COMPLAINT_STATUSES)


@student_bp.route('/laundry')
@login_required
@student_only
def laundry_history():
    """View all laundry orders submitted by the student."""
    status_filter = request.args.get('status', 'All')
    page = request.args.get('page', 1, type=int)
    
    query = Laundry.query.filter_by(student_id=current_user.student_id)
    if status_filter != 'All':
        query = query.filter(Laundry.status == status_filter)
        
    laundry_orders = query.order_by(Laundry.date.desc()).paginate(page=page, per_page=10, error_out=False)
    
    from sqlalchemy import func
    counts = db.session.query(Laundry.status, func.count(Laundry.laundry_id)).filter_by(student_id=current_user.student_id).group_by(Laundry.status).all()
    status_counts = {'All': 0, 'Pending': 0, 'Washing': 0, 'Ready': 0, 'Collected': 0}
    for status, count in counts:
        if status in status_counts:
            status_counts[status] = count
            status_counts['All'] += count
            
    return render_template('student/laundry.html', 
                          laundry_orders=laundry_orders, 
                          status_counts=status_counts,
                          current_status=status_filter)


@student_bp.route('/laundry/new', methods=['GET', 'POST'])
@login_required
@student_only
def new_laundry():
    """Place a new laundry order."""
    from datetime import date, datetime
    today_date = date.today()
    
    if request.method == 'POST':
        weight_str = request.form.get('weight', '')
        items = request.form.get('items', '').strip()
        pickup_date_str = request.form.get('pickup_date', '').strip()
        special_instructions = request.form.get('special_instructions', '').strip()

        try:
            weight = float(weight_str)
            if weight <= 0 or weight > 20:
                raise ValueError
        except ValueError:
            flash('Invalid weight. Must be greater than 0 and up to 20 kg.', 'danger')
            return redirect(url_for('student.new_laundry'))
            
        pickup_date = None
        if pickup_date_str:
            try:
                pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
                if pickup_date < today_date:
                    flash('Pickup date cannot be in the past.', 'danger')
                    return redirect(url_for('student.new_laundry'))
            except ValueError:
                flash('Invalid date format.', 'danger')
                return redirect(url_for('student.new_laundry'))

        laundry = Laundry(
            student_id=current_user.student_id,
            date=today_date,
            weight=weight,
            items=items,
            status='Pending',
            pickup_date=pickup_date,
            special_instructions=special_instructions if special_instructions else None
        )
        db.session.add(laundry)
        db.session.commit()
        flash('Laundry order placed successfully.', 'success')
        return redirect(url_for('student.laundry_history'))

    return render_template('student/new_laundry.html', today=today_date.strftime('%Y-%m-%d'))


@student_bp.route('/complaint/<int:complaint_id>/feedback', methods=['GET', 'POST'])
@login_required
@student_only
def complaint_feedback(complaint_id):
    """Submit feedback for a resolved complaint."""
    from app.models import Feedback
    complaint = db.get_or_404(Complaint, complaint_id)

    # Ownership check — must come first, before any status check
    if complaint.student_id != current_user.student_id:
        abort(403)
    if complaint.status != 'Resolved':
        flash('Feedback can only be provided for resolved complaints.', 'error')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        comments = request.form.get('comments', '').strip()
        if not comments:
            flash('Please enter your feedback comments.', 'error')
            return redirect(url_for('student.complaint_feedback', complaint_id=complaint_id))

        from sqlalchemy import func
        from sqlalchemy.exc import IntegrityError

        def _insert_feedback():
            max_serial = db.session.query(func.max(Feedback.serial_no)).scalar() or 0
            fb = Feedback(
                complaint_id=complaint_id,
                serial_no=max_serial + 1,
                comments=comments,
            )
            db.session.add(fb)
            db.session.commit()

        try:
            _insert_feedback()
        except IntegrityError:
            db.session.rollback()
            _insert_feedback()  # retry once on collision

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/complaint_feedback.html', complaint=complaint)


@student_bp.route('/complaint/<int:complaint_id>/track')
@login_required
@student_only
def track_complaint(complaint_id):
    """View the tracking timeline for a specific complaint."""
    complaint = db.get_or_404(Complaint, complaint_id)
    if complaint.student_id != current_user.student_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/complaint_track.html', complaint=complaint)


@student_bp.route('/profile')
@login_required
@student_only
def profile():
    student = db.session.get(Student, current_user.student_id)
    
    active_allocation = RoomAllocation.query.options(
        db.joinedload(RoomAllocation.room).joinedload(Room.hostel)
    ).filter_by(
        student_id=student.student_id, vacate_date=None
    ).first()
    
    from sqlalchemy import func
    att_counts = db.session.query(Attendance.status, func.count(Attendance.student_id)).filter_by(
        student_id=student.student_id
    ).group_by(Attendance.status).all()
    
    attendance_summary = {'present': 0, 'absent': 0, 'leave': 0}
    for status, count in att_counts:
        st = status.value.lower()
        if st in attendance_summary:
            attendance_summary[st] = count
            
    total_complaints = Complaint.query.filter_by(student_id=student.student_id).count()
    open_complaints = Complaint.query.filter_by(student_id=student.student_id, status='Open').count()
    
    return render_template('student/profile.html', 
                          student=student, 
                          active_allocation=active_allocation, 
                          attendance_summary=attendance_summary, 
                          total_complaints=total_complaints, 
                          open_complaints=open_complaints)


@student_bp.route('/profile/edit', methods=['POST'])
@login_required
@student_only
def edit_profile():
    from datetime import datetime
    student = db.session.get(Student, current_user.student_id)
    
    name = request.form.get('name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    gender = request.form.get('gender', '').strip()
    dob_raw = request.form.get('date_of_birth', '').strip()
    address = request.form.get('address', '').strip()
    
    if not name or not phone_number:
        flash('Name and Phone Number are required.', 'danger')
        return redirect(url_for('student.profile'))
        
    student.name = name
    student.phone_number = phone_number
    student.gender = gender if gender else None
    
    if dob_raw:
        try:
            student.date_of_birth = datetime.strptime(dob_raw, '%Y-%m-%d').date()
        except ValueError:
            pass
    else:
        student.date_of_birth = None
    
    student.address = address if address else None
    
    try:
        db.session.commit()
        flash('Profile updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the profile.', 'danger')
        
    return redirect(url_for('student.profile'))
