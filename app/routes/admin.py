from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import (
    AC_Room, Non_AC_Room, Hostel, Room, RoomAllocation, RoomType,
    StaffMember, Student,
)

admin_bp = Blueprint('admin', __name__)


def admin_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_staff', next=request.url))
        if not isinstance(current_user, StaffMember) or current_user.role != 'admin':
            abort(403)
        return view(*args, **kwargs)
    return wrapped


# ── Dashboard ────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@login_required
@admin_only
def dashboard():
    total_hostels = db.session.query(func.count(Hostel.hostel_id)).scalar()
    total_rooms   = db.session.query(func.count(Room.id)).scalar()
    total_students = db.session.query(func.count(Student.student_id)).scalar()
    total_staff   = db.session.query(func.count(StaffMember.staff_id)).scalar()
    hostels = Hostel.query.order_by(Hostel.type).all()
    rooms   = Room.query.order_by(Room.hostel_id, Room.room_no).all()
    return render_template(
        'admin/dashboard.html',
        total_hostels=total_hostels,
        total_rooms=total_rooms,
        total_students=total_students,
        total_staff=total_staff,
        hostels=hostels,
        rooms=rooms,
    )


# ── Hostel Management ────────────────────────────────────────────────────────

@admin_bp.route('/hostel/new', methods=['GET', 'POST'])
@login_required
@admin_only
def new_hostel():
    if request.method == 'POST':
        h_type   = request.form.get('type', '').strip()
        no_rooms = request.form.get('no_of_rooms', '').strip()
        contact  = request.form.get('hostel_contact', '').strip()
        if not h_type or not no_rooms or not contact:
            flash('All fields are required.', 'error')
            return render_template('admin/hostel_form.html', hostel=None)
        try:
            no_rooms = int(no_rooms)
        except ValueError:
            flash('Number of rooms must be a number.', 'error')
            return render_template('admin/hostel_form.html', hostel=None)
        hostel = Hostel(type=h_type, no_of_rooms=no_rooms, hostel_contact=contact)
        db.session.add(hostel)
        db.session.commit()
        flash(f'Hostel "{h_type}" created successfully.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/hostel_form.html', hostel=None)


@admin_bp.route('/hostel/<int:hostel_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_hostel(hostel_id):
    hostel = db.get_or_404(Hostel, hostel_id)
    if request.method == 'POST':
        h_type   = request.form.get('type', '').strip()
        no_rooms = request.form.get('no_of_rooms', '').strip()
        contact  = request.form.get('hostel_contact', '').strip()
        if not h_type or not no_rooms or not contact:
            flash('All fields are required.', 'error')
            return render_template('admin/hostel_form.html', hostel=hostel)
        try:
            no_rooms = int(no_rooms)
        except ValueError:
            flash('Number of rooms must be a number.', 'error')
            return render_template('admin/hostel_form.html', hostel=hostel)
        hostel.type = h_type
        hostel.no_of_rooms = no_rooms
        hostel.hostel_contact = contact
        db.session.commit()
        flash('Hostel updated successfully.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/hostel_form.html', hostel=hostel)


@admin_bp.route('/hostel/<int:hostel_id>/delete', methods=['POST'])
@login_required
@admin_only
def delete_hostel(hostel_id):
    hostel = db.get_or_404(Hostel, hostel_id)
    # Check for active room allocations in any room of this hostel
    active = (
        db.session.query(RoomAllocation)
        .join(Room, RoomAllocation.room_id == Room.id)
        .filter(Room.hostel_id == hostel_id, RoomAllocation.vacate_date.is_(None))
        .first()
    )
    if active:
        flash('Cannot delete hostel — it has active room allocations.', 'danger')
        return redirect(url_for('admin.dashboard'))
    db.session.delete(hostel)
    db.session.commit()
    flash('Hostel deleted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))


# ── Room Management ──────────────────────────────────────────────────────────

@admin_bp.route('/room/new', methods=['GET', 'POST'])
@login_required
@admin_only
def new_room():
    hostels = Hostel.query.order_by(Hostel.type).all()
    if request.method == 'POST':
        hostel_id = request.form.get('hostel_id', '').strip()
        room_no   = request.form.get('room_no', '').strip()
        room_type = request.form.get('room_type', '').strip()
        capacity  = request.form.get('capacity', '').strip()
        if not hostel_id or not room_no or not room_type or not capacity:
            flash('All fields are required.', 'error')
            return render_template('admin/room_form.html', hostels=hostels)
        try:
            hostel_id = int(hostel_id)
            capacity  = int(capacity)
        except ValueError:
            flash('Invalid numeric values.', 'error')
            return render_template('admin/room_form.html', hostels=hostels)

        if room_type == 'AC':
            room = AC_Room(
                hostel_id=hostel_id, room_no=room_no,
                room_type=RoomType.AC, capacity=capacity
            )
        else:
            room = Non_AC_Room(
                hostel_id=hostel_id, room_no=room_no,
                room_type=RoomType.NON_AC, capacity=capacity
            )
        db.session.add(room)
        try:
            db.session.commit()
            flash(f'Room {room_no} created successfully.', 'success')
        except Exception:
            db.session.rollback()
            flash('Room number already exists in that hostel.', 'danger')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/room_form.html', hostels=hostels)


@admin_bp.route('/room/<int:room_id>/delete', methods=['POST'])
@login_required
@admin_only
def delete_room(room_id):
    room = db.get_or_404(Room, room_id)
    active = RoomAllocation.query.filter_by(room_id=room_id, vacate_date=None).first()
    if active:
        flash('Cannot delete room — it has an active allocation.', 'danger')
        return redirect(url_for('admin.dashboard'))
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))
