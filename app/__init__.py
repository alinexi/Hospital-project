import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Medical Records App startup')
    
    # Import models to ensure they are registered with SQLAlchemy
    from app import models
    
    # Register blueprints
    from app.views.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.views.sysadmin import bp as sysadmin_bp
    app.register_blueprint(sysadmin_bp, url_prefix='/sysadmin')
    
    from app.views.receptionist import bp as receptionist_bp
    app.register_blueprint(receptionist_bp, url_prefix='/receptionist')
    
    from app.views.chief_doctor import bp as chief_doctor_bp
    app.register_blueprint(chief_doctor_bp, url_prefix='/chief_doctor')
    
    from app.views.curing_doctor import bp as curing_doctor_bp
    app.register_blueprint(curing_doctor_bp, url_prefix='/curing_doctor')
    
    from app.views.special_doctor import bp as special_doctor_bp
    app.register_blueprint(special_doctor_bp, url_prefix='/special_doctor')
    
    from app.views.patient import bp as patient_bp
    app.register_blueprint(patient_bp, url_prefix='/patient')
    
    # Main route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'sysadmin':
                return redirect(url_for('sysadmin.dashboard'))
            elif current_user.role == 'receptionist':
                return redirect(url_for('receptionist.dashboard'))
            elif current_user.role == 'chief_doctor':
                return redirect(url_for('chief_doctor.dashboard'))
            elif current_user.role == 'curing_doctor':
                return redirect(url_for('curing_doctor.dashboard'))
            elif current_user.role == 'special_doctor':
                return redirect(url_for('special_doctor.dashboard'))
            elif current_user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        return redirect(url_for('auth.login'))
    
    # CLI command for database initialization
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database"""
        from app.utils.encryption import generate_rsa_keys
        
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()
        
        # Generate RSA keys if not present
        generate_rsa_keys()
        
        # Create default users for testing
        from app.models import User
        from werkzeug.security import generate_password_hash
        
        default_users = [
            {'username': 'admin', 'email': 'admin@hospital.com', 'password': 'admin123', 'role': 'sysadmin'},
            {'username': 'receptionist1', 'email': 'receptionist@hospital.com', 'password': 'recept123', 'role': 'receptionist'},
            {'username': 'chief1', 'email': 'chief@hospital.com', 'password': 'chief123', 'role': 'chief_doctor'},
            {'username': 'doctor1', 'email': 'doctor@hospital.com', 'password': 'doctor123', 'role': 'curing_doctor'},
            {'username': 'specialist1', 'email': 'specialist@hospital.com', 'password': 'spec123', 'role': 'special_doctor'},
            {'username': 'patient1', 'email': 'patient@example.com', 'password': 'patient123', 'role': 'patient'},
        ]
        
        for user_data in default_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role']
            )
            db.session.add(user)
        
        db.session.commit()
        print('Database initialized with default users.')
    
    return app 