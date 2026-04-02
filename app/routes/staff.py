from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import Complaint, StaffMember, TaskAllocation

staff_bp = Blueprint('staff', __name__)


def staff_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_staff', next=request.url))
        if not current_user.get_id().startswith('staff_'):
            flash('This area is for staff only.', 'error')
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@staff_bp.route('/dashboard')
@login_required
@staff_only
def dashboard():
    staff = StaffMember.query.get_or_404(current_user.staff_id)
    tasks = (
        TaskAllocation.query.filter_by(staff_id=staff.staff_id)
        .order_by(TaskAllocation.assigned_date.desc())
        .all()
    )
    complaints = (
        Complaint.query.options(joinedload(Complaint.student))
        .filter_by(staff_id=staff.staff_id)
        .order_by(Complaint.issue_date.desc())
        .all()
    )

    # Summary data
    total_tasks = len(tasks)
    pending_tasks = sum(1 for t in tasks if t.status == 'Pending')
    completed_tasks = sum(1 for t in tasks if t.status == 'Completed')

    return render_template(
        'staff/dashboard.html',
        staff=staff,
        tasks=tasks,
        complaints=complaints,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
    )


@staff_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required
@staff_only
def complete_task(task_id):
    """Mark a task as Completed."""
    task = db.session.get(TaskAllocation, task_id)
    if task is None:
        abort(404)
    # Only the assigned staff member can mark it complete
    if task.staff_id != current_user.staff_id:
        flash('You can only complete tasks assigned to you.', 'error')
        return redirect(url_for('staff.dashboard'))
    if task.status == 'Completed':
        flash('Task is already marked as completed.', 'info')
        return redirect(url_for('staff.dashboard'))
    task.status = 'Completed'
    task.completed_date = date.today()
    db.session.commit()
    flash(f'Task #{task.task_id} marked as completed.', 'success')
    return redirect(url_for('staff.dashboard'))
@staff_bp.route('/complaint/<int:complaint_id>/update', methods=['POST'])
@login_required
@staff_only
def update_complaint_status(complaint_id):
    """Update the status of an assigned complaint."""
    complaint = Complaint.query.get_or_404(complaint_id)
    if complaint.staff_id != current_user.staff_id:
        flash('You can only update complaints assigned to you.', 'error')
        return redirect(url_for('staff.dashboard'))
    
    new_status = request.form.get('status', '').strip()
    if new_status in ['In Progress', 'Resolved']:
        complaint.status = new_status
        db.session.commit()
        flash(f'Complaint status updated to {new_status}.', 'success')
    else:
        flash('Invalid status selected.', 'error')
        
    return redirect(url_for('staff.dashboard'))
