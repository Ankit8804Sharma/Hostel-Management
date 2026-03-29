from flask import Flask, redirect, request, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

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


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

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
        return redirect(url_for('auth.login_student'))

    return app
