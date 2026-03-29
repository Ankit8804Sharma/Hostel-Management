from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Complaint, RoomAllocation, StaffMember, Warden

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
            flash('Warden access only.', 'error')
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@warden_bp.route('/dashboard')
@login_required
@warden_only
def dashboard():
    complaints = Complaint.query.order_by(Complaint.issue_date.desc()).all()
    allocations = (
        RoomAllocation.query.order_by(RoomAllocation.alloc_date.desc()).all()
    )
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    return render_template(
        'warden/dashboard.html',
        complaints=complaints,
        allocations=allocations,
        staff_members=staff_members,
    )
