from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Attendance, Complaint, Laundry, Student

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
        .limit(60)
        .all()
    )
    return render_template(
        'student/dashboard.html',
        student=student,
        complaints=complaints,
        laundry_orders=laundry_orders,
        attendance=attendance,
        complaint_categories=sorted(COMPLAINT_CATEGORIES),
    )


@student_bp.route('/complaint/new', methods=['POST'])
@login_required
@student_only
def new_complaint():
    complaint_type = request.form.get('type', '').strip()
    description = request.form.get('description', '').strip()
    if complaint_type not in COMPLAINT_CATEGORIES or not description:
        flash('Please choose a category and enter a description.', 'error')
        return redirect(url_for('student.dashboard'))
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
