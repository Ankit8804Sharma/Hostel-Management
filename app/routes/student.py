from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Attendance, Complaint, Laundry, Student

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
    )
