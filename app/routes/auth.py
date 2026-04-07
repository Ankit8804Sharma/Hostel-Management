import os
import re
from urllib.parse import urljoin, urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from app import db
from app.models import StaffMember, Student
from app import limiter

auth_bp = Blueprint('auth', __name__)


def _is_safe_url(target: str) -> bool:
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        if not all([name, email, phone, password]):
            flash('All fields are required.', 'error')
            return render_template('auth/register_student.html')
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format.', 'error')
            return render_template('auth/register_student.html')
        if Student.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register_student.html')
        student = Student(name=name, email=email, phone_number=phone)
        student.set_password(password)
        db.session.add(student)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login_student'))
    return render_template('auth/register_student.html')


@auth_bp.route('/login/student', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login_student():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.form.get('next')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login_student.html', next=next_url)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format.', 'error')
            return render_template('auth/login_student.html', next=next_url)
        user = Student.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('auth/login_student.html', next=next_url)
        login_user(user, remember=bool(request.form.get('remember')))
        if next_url and _is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for('student.dashboard'))
    return render_template('auth/login_student.html', next=request.args.get('next'))


@auth_bp.route('/register/staff', methods=['GET', 'POST'])
def register_staff():
    if request.method == 'POST':
        if request.form.get('invite_code') != os.environ.get('STAFF_INVITE_CODE'):
            abort(403)
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        contact_no = request.form.get('contact_no', '').strip()
        designation = request.form.get('designation', '').strip()
        password = request.form.get('password', '')
        if not all([name, email, contact_no, designation, password]):
            flash('All fields are required.', 'error')
            return render_template('auth/register_staff.html')
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format.', 'error')
            return render_template('auth/register_staff.html')
        if StaffMember.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('auth/register_staff.html')
        staff = StaffMember(
            name=name,
            email=email,
            contact_no=contact_no,
            designation=designation,
            role='staff',
        )
        staff.set_password(password)
        db.session.add(staff)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login_staff'))
    return render_template('auth/register_staff.html')


@auth_bp.route('/login/staff', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login_staff():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.form.get('next')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login_staff.html', next=next_url)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format.', 'error')
            return render_template('auth/login_staff.html', next=next_url)
        user = StaffMember.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('auth/login_staff.html', next=next_url)
        login_user(user, remember=bool(request.form.get('remember')))
        if next_url and _is_safe_url(next_url):
            return redirect(next_url)
        return redirect(url_for('staff.dashboard'))
    return render_template('auth/login_staff.html', next=request.args.get('next'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_student'))
