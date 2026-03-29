from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app import db
from app.models import Complaint, RoomAllocation, StaffMember, Warden

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
            flash('Warden access only.', 'error')
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
    allocations = (
        RoomAllocation.query.order_by(RoomAllocation.alloc_date.desc()).all()
    )
    staff_members = StaffMember.query.order_by(StaffMember.name).all()
    return render_template(
        'warden/dashboard.html',
        complaints=complaints,
        allocations=allocations,
        staff_members=staff_members,
        complaint_statuses=COMPLAINT_STATUSES,
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
