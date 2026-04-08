import os
from flask import Flask, g, redirect, render_template, request, url_for, current_app
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException
from flask_mail import Mail
from config import config_by_name

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login_student'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])
mail = Mail()
from flask_jwt_extended import JWTManager
jwt = JWTManager()
from itsdangerous import URLSafeTimedSerializer

def generate_reset_token(email):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, expiration=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try: 
        return s.loads(token, salt='password-reset-salt', max_age=expiration)
    except: 
        return None


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
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)

    import os as _os
    _os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app import models  # noqa: F401

    from app.routes.auth import auth_bp
    from app.routes.staff import staff_bp
    from app.routes.student import student_bp
    from app.routes.warden import warden_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(warden_bp, url_prefix='/warden')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    
    from app.routes.api import api_bp
    csrf.exempt(api_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        from flask_login import current_user
        from app.models import Student, StaffMember
        if current_user.is_authenticated:
            if isinstance(current_user, Student):
                return redirect(url_for('student.dashboard'))
            elif isinstance(current_user, StaffMember):
                if current_user.role in ('warden', 'chief_warden'):
                    return redirect(url_for('warden.dashboard'))
                return redirect(url_for('staff.dashboard'))
        return render_template('index.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        # pass through HTTP errors
        if isinstance(e, HTTPException):
            return e
        # now you're handling non-HTTP exceptions only
        return render_template('500.html'), 500

    @app.context_processor
    def inject_warden_stats():
        from flask_login import current_user
        from app.models import Complaint, StaffMember
        if current_user.is_authenticated and isinstance(current_user, StaffMember):
            if current_user.role in ('warden', 'chief_warden'):
                if 'open_complaints_count' not in g:
                    g.open_complaints_count = Complaint.query.filter_by(status='Open').count()
                return dict(open_complaints_count=g.open_complaints_count)
        return dict(open_complaints_count=0)

    return app
