from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.models import User, AuditLog
from app.forms import LoginForm, RegistrationForm
import json

bp = Blueprint('auth', __name__)

def role_required(role):
    """Decorator to enforce role-based access control"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                flash('Access denied. Insufficient privileges.', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action, target_type=None, target_id=None, details=None):
    """Helper function to log user actions for audit trail"""
    try:
        audit_log = AuditLog(
            user_id=current_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=json.dumps(details) if details else None
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error logging action: {str(e)}")

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()
            
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                log_action('LOGIN')
                flash(f'Welcome, {user.username}!', 'success')
                
                # Redirect to appropriate dashboard based on role
                if user.role == 'sysadmin':
                    return redirect(url_for('sysadmin.dashboard'))
                elif user.role == 'receptionist':
                    return redirect(url_for('receptionist.dashboard'))
                elif user.role == 'chief_doctor':
                    return redirect(url_for('chief_doctor.dashboard'))
                elif user.role == 'curing_doctor':
                    return redirect(url_for('curing_doctor.dashboard'))
                elif user.role == 'special_doctor':
                    return redirect(url_for('special_doctor.dashboard'))
                elif user.role == 'patient':
                    return redirect(url_for('patient.dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    """User logout endpoint"""
    try:
        log_action('LOGOUT')
        logout_user()
        flash('You have been logged out successfully.', 'info')
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        flash('An error occurred during logout.', 'error')
    
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint - Note: In production, this should be restricted"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form) 