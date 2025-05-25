from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, AuditLog
from app.forms import UserForm, SearchForm
from app.views.auth import role_required, log_action
import json

bp = Blueprint('sysadmin', __name__)

@bp.route('/dashboard')
@login_required
@role_required('sysadmin')
def dashboard():
    """Sysadmin dashboard with overview statistics"""
    try:
        # Get summary statistics
        total_users = User.query.count()
        user_counts_by_role = db.session.query(
            User.role, db.func.count(User.id)
        ).group_by(User.role).all()
        
        recent_audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        return render_template('sysadmin/dashboard.html',
                             total_users=total_users,
                             user_counts=dict(user_counts_by_role),
                             recent_logs=recent_audit_logs)
    except Exception as e:
        current_app.logger.error(f"Sysadmin dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('sysadmin/dashboard.html')

@bp.route('/users')
@login_required
@role_required('sysadmin')
def list_users():
    """List all users with search functionality"""
    try:
        search_form = SearchForm()
        users = User.query.all()
        
        if search_form.validate_on_submit():
            query = search_form.query.data
            users = User.query.filter(
                db.or_(
                    User.username.contains(query),
                    User.email.contains(query),
                    User.role.contains(query)
                )
            ).all()
        
        return render_template('sysadmin/list_users.html', users=users, search_form=search_form)
    except Exception as e:
        current_app.logger.error(f"List users error: {str(e)}")
        flash('Error loading users.', 'error')
        return render_template('sysadmin/list_users.html', users=[], search_form=SearchForm())

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('sysadmin')
def create_user():
    """Create a new user"""
    form = UserForm()
    if form.validate_on_submit():
        try:
            # Check if username or email already exists
            existing_user = User.query.filter(
                db.or_(User.username == form.username.data, User.email == form.email.data)
            ).first()
            
            if existing_user:
                flash('Username or email already exists.', 'error')
                return render_template('sysadmin/user_form.html', form=form, title='Create User')
            
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data
            )
            db.session.add(user)
            db.session.commit()
            
            # Log the action
            log_action('CREATE_USER', 'User', user.id, {
                'username': user.username,
                'email': user.email,
                'role': user.role
            })
            
            flash(f'User {user.username} created successfully.', 'success')
            return redirect(url_for('sysadmin.list_users'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create user error: {str(e)}")
            flash('Error creating user. Please try again.', 'error')
    
    return render_template('sysadmin/user_form.html', form=form, title='Create User')

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('sysadmin')
def edit_user(user_id):
    """Edit an existing user"""
    try:
        user = User.query.get_or_404(user_id)
        form = UserForm(obj=user)
        
        if form.validate_on_submit():
            # Store old values for audit log
            old_values = {
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
            
            # Check if username or email conflicts with other users
            existing_user = User.query.filter(
                db.and_(
                    User.id != user_id,
                    db.or_(User.username == form.username.data, User.email == form.email.data)
                )
            ).first()
            
            if existing_user:
                flash('Username or email already exists.', 'error')
                return render_template('sysadmin/user_form.html', form=form, title='Edit User', user=user)
            
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            
            # Update password if provided
            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
            
            db.session.commit()
            
            # Log the action
            new_values = {
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
            log_action('UPDATE_USER', 'User', user.id, {
                'old_values': old_values,
                'new_values': new_values
            })
            
            flash(f'User {user.username} updated successfully.', 'success')
            return redirect(url_for('sysadmin.list_users'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit user error: {str(e)}")
        flash('Error updating user. Please try again.', 'error')
    
    return render_template('sysadmin/user_form.html', form=form, title='Edit User', user=user)

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('sysadmin')
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting self
        if user.id == current_user.id:
            flash('Cannot delete your own account.', 'error')
            return redirect(url_for('sysadmin.list_users'))
        
        username = user.username
        
        # Log before deletion
        log_action('DELETE_USER', 'User', user.id, {
            'username': user.username,
            'email': user.email,
            'role': user.role
        })
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {username} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete user error: {str(e)}")
        flash('Error deleting user. Please try again.', 'error')
    
    return redirect(url_for('sysadmin.list_users'))

@bp.route('/audit-log')
@login_required
@role_required('sysadmin')
def audit_log():
    """View audit log of all user and role changes"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('sysadmin/audit_log.html', logs=logs)
        
    except Exception as e:
        current_app.logger.error(f"Audit log error: {str(e)}")
        flash('Error loading audit log.', 'error')
        return render_template('sysadmin/audit_log.html', logs=None)

@bp.route('/roles')
@login_required
@role_required('sysadmin')
def manage_roles():
    """Manage role definitions and permissions"""
    try:
        # This is a placeholder for role management functionality
        # Students can extend this to define custom permissions per role
        roles = {
            'sysadmin': 'System Administrator - Full access to all functions',
            'receptionist': 'Receptionist - Patient registration and appointment scheduling',
            'chief_doctor': 'Chief Doctor - View all records, assign patients',
            'curing_doctor': 'Curing Doctor - Manage assigned patients and records',
            'special_doctor': 'Special Doctor - Consultant access to granted records',
            'patient': 'Patient - View own information and book appointments'
        }
        
        return render_template('sysadmin/roles.html', roles=roles)
        
    except Exception as e:
        current_app.logger.error(f"Manage roles error: {str(e)}")
        flash('Error loading roles.', 'error')
        return render_template('sysadmin/roles.html', roles={})

# TODO: Students can extend this section with additional sysadmin functionality:
# - Role permission management
# - System configuration
# - Database backup/restore
# - User activity monitoring
# - System health checks 