from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

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
    return render_template(
        'staff/dashboard.html',
        staff=staff,
        tasks=tasks,
        complaints=complaints,
    )
