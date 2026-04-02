from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    Attendance,
    AttendanceStatus,
    Complaint,
    RoomAllocation,
    StaffMember,
    Student,
    TaskAllocation,
    Warden,
)

COMPLAINT_STATUSES = ('Open', 'In Progress', 'Resolved')

warden_bp = Blueprint('warden', __name__)


def warden_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_staff', next=request.url))
        if not current_user.get_id().startswith('staff_'):
            flash('This area is for wardens (staff login).', 'error')
            abort(403)
        warden_row = Warden.query.filter_by(staff_id=current_user.staff_id).first()
        role = getattr(current_user, 'role', None)
        if warden_row is None and role not in ('warden', 'chief_warden'):
            flash('Access denied. Warden access only.', 'danger')
            if current_user.get_id().startswith('student_'):
                return redirect(url_for('student.dashboard'))
            elif role == 'staff':
                return redirect(url_for('staff.dashboard'))
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@warden_bp.route('/dashboard')
@login_required
@warden_only
def dashboard():
    complaints = (
        Complaint.query.options(joinedload(Complaint.student), joinedload(Complaint.staff))
        .order_by(Complaint.issue_date.desc())
        .all()
    )
    # Summary counts for complaints
    total_complaints = len(complaints)
    open_complaints = sum(1 for c in complaints if c.status == 'Open')
    in_progress_complaints = sum(1 for c in complaints if c.status == 'In Progress')
    resolved_complaints = sum(1 for c in complaints if c.status == 'Resolved')

    tasks = (
        TaskAllocation.query.options(joinedload(TaskAllocation.staff))
        .order_by(TaskAllocation.assigned_date.desc())
        .all()
    )

    allocations = (
        RoomAllocation.query.order_by(RoomAllocation.alloc_date.desc()).all()
    )
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    today_attendance = (
        Attendance.query.filter_by(date=date.today())
        .join(Student)
        .order_by(Student.name)
        .all()
    )
    return render_template(
        'warden/dashboard.html',
        complaints=complaints,
        total_complaints=total_complaints,
        open_complaints=open_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints,
        tasks=tasks,
        allocations=allocations,
        staff_members=staff_members,
        complaint_statuses=COMPLAINT_STATUSES,
        today_attendance=today_attendance,
    )


@warden_bp.route('/complaint/<int:complaint_id>/update', methods=['POST'])
@login_required
@warden_only
def update_complaint(complaint_id):
    c = db.session.get(Complaint, complaint_id)
    if c is None:
        abort(404)
    status = request.form.get('status', '').strip()
    if status in COMPLAINT_STATUSES:
        c.status = status
    staff_raw = request.form.get('staff_id', '').strip()
    if staff_raw in ('', 'none', '0', 'unassigned'):
        c.staff_id = None
    else:
        try:
            sid = int(staff_raw)
        except ValueError:
            flash('Invalid staff selection.', 'error')
            return redirect(url_for('warden.dashboard'))
        staff = db.session.get(StaffMember, sid)
        if staff is None:
            flash('That staff member does not exist.', 'error')
            return redirect(url_for('warden.dashboard'))
        c.staff_id = sid
    db.session.commit()
    flash('Complaint updated.', 'success')
    return redirect(url_for('warden.dashboard'))


@warden_bp.route('/complaint/<int:complaint_id>/assign', methods=['POST'])
@login_required
@warden_only
def assign_complaint(complaint_id):
    c = db.session.get(Complaint, complaint_id)
    if c is None:
        abort(404)
    staff_id_raw = request.form.get('staff_id', '').strip()
    if not staff_id_raw:
        flash('Please select a staff member.', 'error')
        return redirect(url_for('warden.dashboard'))
    try:
        staff_id = int(staff_id_raw)
    except ValueError:
        flash('Invalid staff ID.', 'error')
        return redirect(url_for('warden.dashboard'))
    staff = db.session.get(StaffMember, staff_id)
    if not staff:
        flash('Staff member not found.', 'error')
        return redirect(url_for('warden.dashboard'))
    c.staff_id = staff_id
    c.status = 'In Progress'
    db.session.commit()
    flash(f'Complaint assigned to {staff.name}.', 'success')
    return redirect(url_for('warden.dashboard'))


@warden_bp.route('/complaint/<int:complaint_id>/resolve', methods=['POST'])
@login_required
@warden_only
def resolve_complaint(complaint_id):
    c = db.session.get(Complaint, complaint_id)
    if c is None:
        abort(404)
    c.status = 'Resolved'
    db.session.commit()
    flash('Complaint marked as resolved.', 'success')
    return redirect(url_for('warden.dashboard'))


@warden_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@warden_only
def attendance():
    """Manage student attendance: mark for today and view history."""
    from datetime import timedelta
    today = date.today()

    if request.method == 'POST':
        students = Student.query.all()
        saved = 0
        for student in students:
            status_val = request.form.get(f'status_{student.student_id}', '').strip()
            if not status_val:
                continue
            try:
                status_enum = AttendanceStatus(status_val)
            except ValueError:
                continue
            
            # Using tuple for composite PK in db.session.get
            existing = db.session.get(Attendance, (student.student_id, today))
            if existing:
                existing.status = status_enum
            else:
                record = Attendance(
                    student_id=student.student_id,
                    date=today,
                    status=status_enum,
                )
                db.session.add(record)
            saved += 1
        db.session.commit()
        flash(f'Attendance recorded for {saved} students.', 'success')
        return redirect(url_for('warden.attendance'))

    # GET: show form and history
    students = Student.query.order_by(Student.name).all()
    # Fetch already-marked records for today to pre-fill form
    today_records = {
        a.student_id: a.status.value
        for a in Attendance.query.filter_by(date=today).all()
    }
    
    # Fetch last 7 days of history
    seven_days_ago = today - timedelta(days=7)
    history = (
        Attendance.query.filter(Attendance.date >= seven_days_ago)
        .options(joinedload(Attendance.student))
        .order_by(Attendance.date.desc())
        .limit(100) # Safety limit
        .all()
    )

    return render_template(
        'warden/attendance.html',
        students=students,
        today=today,
        existing=today_records,
        history=history,
        statuses=[s.value for s in AttendanceStatus],
    )
@warden_bp.route('/task/new', methods=['GET', 'POST'])
@login_required
@warden_only
def new_task():
    """Create a new maintenance task for staff."""
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        staff_id_raw = request.form.get('staff_id', '').strip()
        
        if not description or not staff_id_raw:
            flash('Description and staff assigned are required.', 'error')
            return redirect(url_for('warden.new_task'))
        
        try:
            staff_id = int(staff_id_raw)
        except ValueError:
            flash('Invalid staff ID.', 'error')
            return redirect(url_for('warden.new_task'))
            
        task = TaskAllocation(
            description=description,
            staff_id=staff_id,
            assigned_date=date.today(),
            status='Pending'
        )
        db.session.add(task)
        db.session.commit()
        flash('Task created and assigned successfully.', 'success')
        return redirect(url_for('warden.dashboard'))

    # GET: show form
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    return render_template('warden/new_task.html', staff_members=staff_members)
