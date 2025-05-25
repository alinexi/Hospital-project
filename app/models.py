from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """User model for authentication and role-based access"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # sysadmin, receptionist, chief_doctor, curing_doctor, special_doctor, patient
    
    # Relationships
    authored_records = db.relationship('MedicalRecord', foreign_keys='MedicalRecord.author_id', backref='author', lazy='dynamic')
    assigned_patients = db.relationship('PatientAssignment', foreign_keys='PatientAssignment.doctor_id', backref='assigned_doctor', lazy='dynamic')
    access_grants = db.relationship('AccessGrant', foreign_keys='AccessGrant.granted_to_user_id', backref='granted_user', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash for the user"""
        self.password_hash = generate_password_hash(password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Patient(db.Model):
    """Patient model for storing patient information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    demographics = db.Column(db.Text)  # JSON or text field for demographics
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Link to User if patient has account
    
    # Relationships
    user = db.relationship('User', backref='patient_profile')
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('PatientAssignment', backref='patient', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.name}>'

class PatientAssignment(db.Model):
    """Assignment of patients to curing doctors"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PatientAssignment Patient:{self.patient_id} Doctor:{self.doctor_id}>'

class Appointment(db.Model):
    """Appointment model for scheduling"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled, rescheduled
    notes = db.Column(db.Text)
    
    # Relationship to doctor
    doctor = db.relationship('User', backref='appointments')
    
    def __repr__(self):
        return f'<Appointment {self.id}: Patient {self.patient_id} with Doctor {self.doctor_id}>'

class MedicalRecord(db.Model):
    """Medical record model with encryption"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    encrypted_blob = db.Column(db.LargeBinary, nullable=False)  # Encrypted medical data
    signature = db.Column(db.LargeBinary, nullable=False)  # Digital signature
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    record_type = db.Column(db.String(50), default='general')  # general, diagnosis, treatment, etc.
    
    # Relationships
    access_grants = db.relationship('AccessGrant', backref='record', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MedicalRecord {self.id} for Patient {self.patient_id}>'

class AccessGrant(db.Model):
    """Access grants for special doctors to view specific medical records"""
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('medical_record.id'), nullable=False)
    granted_to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    granted_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    granted_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to granting user
    granted_by = db.relationship('User', foreign_keys=[granted_by_user_id], backref='granted_accesses')
    
    def __repr__(self):
        return f'<AccessGrant Record:{self.record_id} To:{self.granted_to_user_id}>'

class AuditLog(db.Model):
    """Audit log for tracking user and role changes"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # CREATE_USER, UPDATE_ROLE, etc.
    target_id = db.Column(db.Integer)  # ID of affected entity
    target_type = db.Column(db.String(50))  # User, Patient, etc.
    details = db.Column(db.Text)  # JSON details of the change
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user who performed the action
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>' 