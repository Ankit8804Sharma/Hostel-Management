import os
from flask import Flask, redirect, render_template, request, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login_student'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    from app.models import StaffMember, Student

    if not user_id:
        return None
    if user_id.startswith('student_'):
        pk = int(user_id.split('_', 1)[1])
        return db.session.get(Student, pk)
    if user_id.startswith('staff_'):
        pk = int(user_id.split('_', 1)[1])
        return db.session.get(StaffMember, pk)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint in ('staff', 'warden'):
        return redirect(url_for('auth.login_staff', next=request.url))
    return redirect(url_for('auth.login_student', next=request.url))


def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.staff import staff_bp
    from app.routes.student import student_bp
    from app.routes.warden import warden_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(warden_bp, url_prefix='/warden')
    app.register_blueprint(staff_bp, url_prefix='/staff')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.context_processor
    def inject_warden_stats():
        from flask_login import current_user
        from app.models import Complaint, StaffMember
        if current_user.is_authenticated and isinstance(current_user, StaffMember):
            if current_user.role in ('warden', 'chief_warden'):
                count = Complaint.query.filter_by(status='Open').count()
                return dict(open_complaints_count=count)
        return dict(open_complaints_count=0)

    return app
