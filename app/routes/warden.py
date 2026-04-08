import csv
import io
import json
from datetime import date, timedelta, datetime
from functools import wraps

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    Attendance,
    AttendanceStatus,
    Complaint,
    Hostel,
    Room,
    RoomAllocation,
    StaffMember,
    Student,
    TaskAllocation,
    Warden,
)
from app.utils.email import send_task_assigned

COMPLAINT_STATUSES = ('Open', 'In Progress', 'Resolved')

warden_bp = Blueprint('warden', __name__)


def warden_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_staff', next=request.url))
        
        # Must be staff a member and have a warden role
        if isinstance(current_user, StaffMember):
            # Check if this staff member has warden role or is listed in warden table
            is_warden = current_user.role in ('warden', 'chief_warden')
            if not is_warden:
                flash('Access denied. Warden access only.', 'danger')
                if current_user.role == 'staff':
                    return redirect(url_for('staff.dashboard'))
                abort(403)
        else:
            flash('This area is for wardens only.', 'error')
            if isinstance(current_user, Student):
                return redirect(url_for('student.dashboard'))
            abort(403)
            
        return view(*args, **kwargs)

    return wrapped


@warden_bp.route('/dashboard')
@login_required
@warden_only
def dashboard():
    # 1. Aggregate counts via SQL — no full table scan
    total_complaints = db.session.query(func.count(Complaint.complaint_id)).scalar() or 0
    open_complaints = db.session.query(func.count(Complaint.complaint_id)).filter(Complaint.status == 'Open').scalar() or 0
    in_progress_complaints = db.session.query(func.count(Complaint.complaint_id)).filter(Complaint.status == 'In Progress').scalar() or 0
    resolved_complaints = db.session.query(func.count(Complaint.complaint_id)).filter(Complaint.status == 'Resolved').scalar() or 0

    # Status Data for Chart (from the counts already computed)
    status_data = {
        'labels': ['Open', 'In Progress', 'Resolved'],
        'counts': [open_complaints, in_progress_complaints, resolved_complaints]
    }

    # Type Data for Chart — single GROUP BY query
    complaint_types = ['Electrical', 'Plumbing', 'Internet', 'Cleanliness', 'Furniture', 'Other']
    type_count_rows = (
        db.session.query(Complaint.type, func.count(Complaint.complaint_id))
        .group_by(Complaint.type)
        .all()
    )
    type_count_map = {t: c for t, c in type_count_rows}
    type_counts = [type_count_map.get(t, 0) for t in complaint_types]
    type_data = {
        'labels': complaint_types,
        'counts': type_counts
    }

    # 2. Apply Filters for the Table
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'All')
    type_filter = request.args.get('type', 'All')
    page = request.args.get('page', 1, type=int)

    query = Complaint.query.options(joinedload(Complaint.student), joinedload(Complaint.staff))

    if search:
        query = query.join(Student).filter(
            or_(
                Student.name.ilike(f'%{search}%'),
                Complaint.description.ilike(f'%{search}%')
            )
        )

    if status_filter != 'All':
        query = query.filter(Complaint.status == status_filter)

    if type_filter != 'All':
        query = query.filter(Complaint.type == type_filter)

    # Paginate instead of loading all rows
    complaints = query.order_by(Complaint.complaint_id.desc()).paginate(page=page, per_page=20, error_out=False)

    # Generic dashboard data
    tasks = (
        TaskAllocation.query.options(joinedload(TaskAllocation.staff))
        .order_by(TaskAllocation.assigned_date.desc())
        .all()
    )
    allocations = RoomAllocation.query.order_by(RoomAllocation.alloc_date.desc()).all()
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    today_attendance = Attendance.query.filter_by(date=date.today()).join(Student).order_by(Student.name).all()

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
        complaint_types=complaint_types,
        today_attendance=today_attendance,
        status_chart_json=json.dumps(status_data),
        type_chart_json=json.dumps(type_data),
        filters={'search': search, 'status': status_filter, 'type': type_filter}
    )


@warden_bp.route('/overview')
@login_required
@warden_only
def overview():
    total_students = Student.query.count()
    total_staff = StaffMember.query.count()
    total_rooms = Room.query.count()
    total_complaints = Complaint.query.count()

    # Room Occupancy
    occupied_room_ids = db.session.query(RoomAllocation.room_id).filter(RoomAllocation.vacate_date == None).distinct().all()
    occupied_room_count = len(occupied_room_ids)
    occupancy_rate = (occupied_room_count / total_rooms * 100) if total_rooms > 0 else 0

    # Staff Performance
    staff_perf = []
    all_staff = StaffMember.query.all()
    for s in all_staff:
        total = s.tasks.count()
        completed = s.tasks.filter(TaskAllocation.completed_date != None).count()
        pending = total - completed
        rate = (completed / total * 100) if total > 0 else 0
        staff_perf.append({
            'name': s.name,
            'total': total,
            'completed': completed,
            'pending': pending,
            'rate': round(rate, 1)
        })

    # Top 3 Complaints
    top_complaints = db.session.query(Complaint.type, func.count(Complaint.complaint_id).label('count'))\
        .group_by(Complaint.type).order_by(func.count(Complaint.complaint_id).desc()).limit(3).all()

    # Monthly Trend (Last 30 days)
    last_30_days = date.today() - timedelta(days=30)
    history = db.session.query(Complaint.issue_date, func.count(Complaint.complaint_id))\
        .filter(Complaint.issue_date >= last_30_days)\
        .group_by(Complaint.issue_date).order_by(Complaint.issue_date).all()
    
    trend_labels = [h[0].strftime('%b %d') for h in history]
    trend_counts = [h[1] for h in history]

    return render_template('warden/overview.html',
        total_students=total_students,
        total_staff=total_staff,
        total_rooms=total_rooms,
        total_complaints=total_complaints,
        occupied_room_count=occupied_room_count,
        occupancy_rate=round(occupancy_rate, 1),
        staff_performance=staff_perf,
        top_complaints=top_complaints,
        trend_json=json.dumps({'labels': trend_labels, 'counts': trend_counts})
    )


@warden_bp.route('/students')
@login_required
@warden_only
def students():
    search = request.args.get('search', '').strip()

    # Eager-load active allocations and their rooms in a single query (avoids N+1)
    query = Student.query.options(
        joinedload(Student.room_allocations).joinedload(RoomAllocation.room)
    )

    if search:
        query = query.filter(or_(
            Student.name.ilike(f'%{search}%'),
            Student.email.ilike(f'%{search}%')
        ))

    all_students = query.all()
    student_data = []
    for s in all_students:
        # Filter in Python — allocations already loaded, no extra queries
        active_allocs = [a for a in s.room_allocations if a.vacate_date is None]
        alloc = active_allocs[0] if active_allocs else None
        student_data.append({
            'name': s.name,
            'email': s.email,
            'phone': s.phone_number,
            'room_no': alloc.room.room_no if alloc and alloc.room else 'Not Allocated',
            'room_type': alloc.room.room_type.value if alloc and alloc.room else '—',
            'alloc_date': alloc.alloc_date if alloc else '—'
        })

    return render_template('warden/students.html',
        students=student_data,
        search=search,
        total_count=len(student_data))


@warden_bp.route('/complaints/export')
@login_required
@warden_only
def export_complaints():
    complaints = Complaint.query.options(joinedload(Complaint.student), joinedload(Complaint.staff)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Complaint ID', 'Student Name', 'Type', 'Description', 'Status', 'Date', 'Assigned Staff'])
    
    for c in complaints:
        writer.writerow([
            c.complaint_id,
            c.student.name if c.student else '—',
            c.type,
            c.description,
            c.status,
            c.issue_date,
            c.staff.name if c.staff else 'Unassigned'
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=complaints_export.csv"}
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
            
        priority = request.form.get('priority', 'Medium').strip()
        due_date_raw = request.form.get('due_date', '').strip()
        due_date = datetime.strptime(due_date_raw, '%Y-%m-%d').date() if due_date_raw else None
        
        task = TaskAllocation(
            description=description,
            staff_id=staff_id,
            assigned_date=date.today(),
            due_date=due_date,
            priority=priority,
            status='Pending'
        )
        db.session.add(task)
        db.session.commit()
        assigned_staff = db.session.get(StaffMember, staff_id)
        if assigned_staff:
            send_task_assigned(assigned_staff.email, assigned_staff.name, task.description, current_user.name)
        flash('Task created and assigned successfully.', 'success')
        return redirect(url_for('warden.dashboard'))

    # GET: show form
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    return render_template('warden/new_task.html', staff_members=staff_members)


@warden_bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
@warden_only
def delete_task(task_id):
    """Delete a task."""
    task = db.session.get(TaskAllocation, task_id)
    if not task:
        abort(404)
        
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('warden.dashboard'))



@warden_bp.route('/room-management')
@login_required
@warden_only
def room_management():
    """Show all students with their current active room allocation."""
    # Left outer join: every student, with their active allocation (if any)
    rows = (
        db.session.query(Student, RoomAllocation, Room)
        .outerjoin(
            RoomAllocation,
            (RoomAllocation.student_id == Student.student_id) &
            (RoomAllocation.vacate_date.is_(None))
        )
        .outerjoin(Room, Room.id == RoomAllocation.room_id)
        .order_by(Student.name)
        .all()
    )

    # Unoccupied rooms only (no active allocation)
    occupied_room_ids = db.session.query(RoomAllocation.room_id).filter(
        RoomAllocation.vacate_date.is_(None)
    ).subquery()
    available_rooms = (
        Room.query
        .filter(~Room.id.in_(occupied_room_ids))
        .order_by(Room.room_no)
        .all()
    )

    # Students with no active allocation (eligible to be allocated)
    allocated_student_ids = db.session.query(RoomAllocation.student_id).filter(
        RoomAllocation.vacate_date.is_(None)
    ).subquery()
    unallocated_students = (
        Student.query
        .filter(~Student.student_id.in_(allocated_student_ids))
        .order_by(Student.name)
        .all()
    )

    return render_template(
        'warden/room_management.html',
        rows=rows,
        available_rooms=available_rooms,
        unallocated_students=unallocated_students,
    )


@warden_bp.route('/room/allocate', methods=['POST'])
@login_required
@warden_only
def allocate_room():
    """Allocate an available room to an unallocated student."""
    student_id = request.form.get('student_id', type=int)
    room_id = request.form.get('room_id', type=int)

    if not student_id or not room_id:
        flash('Student and room are required.', 'danger')
        return redirect(url_for('warden.room_management'))

    # Guard: room must not already be actively occupied
    existing = RoomAllocation.query.filter_by(
        room_id=room_id, vacate_date=None
    ).first()
    if existing:
        flash('That room is already occupied.', 'danger')
        return redirect(url_for('warden.room_management'))

    # Guard: student must not already have an active allocation
    student_alloc = RoomAllocation.query.filter_by(
        student_id=student_id, vacate_date=None
    ).first()
    if student_alloc:
        flash('That student already has an active room allocation.', 'danger')
        return redirect(url_for('warden.room_management'))

    allocation = RoomAllocation(
        student_id=student_id,
        room_id=room_id,
        alloc_date=date.today(),
    )
    db.session.add(allocation)
    db.session.commit()
    flash('Room allocated successfully.', 'success')
    return redirect(url_for('warden.room_management'))


@warden_bp.route('/room/vacate/<int:allocation_id>', methods=['POST'])
@login_required
@warden_only
def vacate_room(allocation_id):
    """Mark an active room allocation as vacated."""
    allocation = db.get_or_404(RoomAllocation, allocation_id)
    if allocation.vacate_date is not None:
        flash('This allocation is already vacated.', 'warning')
        return redirect(url_for('warden.room_management'))
    allocation.vacate_date = date.today()
    db.session.commit()
    flash('Room vacated successfully.', 'success')
    return redirect(url_for('warden.room_management'))
