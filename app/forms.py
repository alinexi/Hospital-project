from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SelectField, DateField, DateTimeLocalField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional
from app.models import User, Patient

class LoginForm(FlaskForm):
    """Login form for authentication"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    """Registration form for new users"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('patient', 'Patient'),
        ('receptionist', 'Receptionist'),
        ('curing_doctor', 'Curing Doctor'),
        ('special_doctor', 'Special Doctor'),
        ('chief_doctor', 'Chief Doctor'),
        ('sysadmin', 'System Administrator')
    ], validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

# Sysadmin Forms
class UserForm(FlaskForm):
    """Form for creating/editing users"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('patient', 'Patient'),
        ('receptionist', 'Receptionist'),
        ('curing_doctor', 'Curing Doctor'),
        ('special_doctor', 'Special Doctor'),
        ('chief_doctor', 'Chief Doctor'),
        ('sysadmin', 'System Administrator')
    ], validators=[DataRequired()])
    submit = SubmitField('Save User')

# Receptionist Forms
class PatientForm(FlaskForm):
    """Form for registering/editing patients"""
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    demographics = TextAreaField('Demographics (Address, Phone, Emergency Contact, etc.)')
    submit = SubmitField('Save Patient')

class AppointmentForm(FlaskForm):
    """Form for scheduling appointments"""
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    datetime = DateTimeLocalField('Appointment Date & Time', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled')
    ], default='scheduled')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Appointment')
    
    def __init__(self, *args, **kwargs):
        super(AppointmentForm, self).__init__(*args, **kwargs)
        # Populate patient choices
        self.patient_id.choices = [(p.id, p.name) for p in Patient.query.all()]
        # Populate doctor choices (doctors only)
        self.doctor_id.choices = [(u.id, u.username) for u in User.query.filter(
            User.role.in_(['curing_doctor', 'special_doctor', 'chief_doctor'])
        ).all()]

# Medical Record Forms
class MedicalRecordForm(FlaskForm):
    """Form for creating/editing medical records"""
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    record_type = SelectField('Record Type', choices=[
        ('general', 'General'),
        ('diagnosis', 'Diagnosis'),
        ('treatment', 'Treatment'),
        ('prescription', 'Prescription'),
        ('lab_results', 'Lab Results'),
        ('imaging', 'Imaging'),
        ('surgery', 'Surgery'),
        ('discharge', 'Discharge Summary')
    ], default='general')
    chief_complaint = TextAreaField('Chief Complaint')
    history_present_illness = TextAreaField('History of Present Illness')
    physical_examination = TextAreaField('Physical Examination')
    diagnosis = TextAreaField('Diagnosis')
    treatment_plan = TextAreaField('Treatment Plan')
    medications = TextAreaField('Medications')
    lab_results = TextAreaField('Lab Results')
    notes = TextAreaField('Additional Notes')
    submit = SubmitField('Save Medical Record')
    
    def __init__(self, *args, **kwargs):
        super(MedicalRecordForm, self).__init__(*args, **kwargs)
        # Populate patient choices
        self.patient_id.choices = [(p.id, p.name) for p in Patient.query.all()]

class AccessGrantForm(FlaskForm):
    """Form for granting access to special doctors"""
    record_id = IntegerField('Medical Record ID', validators=[DataRequired()])
    special_doctor_id = SelectField('Special Doctor', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Grant Access')
    
    def __init__(self, *args, **kwargs):
        super(AccessGrantForm, self).__init__(*args, **kwargs)
        # Populate special doctor choices
        self.special_doctor_id.choices = [(u.id, u.username) for u in User.query.filter_by(role='special_doctor').all()]

class PatientAssignmentForm(FlaskForm):
    """Form for assigning patients to curing doctors"""
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Curing Doctor', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Patient')
    
    def __init__(self, *args, **kwargs):
        super(PatientAssignmentForm, self).__init__(*args, **kwargs)
        # Populate patient choices
        self.patient_id.choices = [(p.id, p.name) for p in Patient.query.all()]
        # Populate curing doctor choices
        self.doctor_id.choices = [(u.id, u.username) for u in User.query.filter_by(role='curing_doctor').all()]

# Patient Forms
class PatientProfileForm(FlaskForm):
    """Form for patients to complete their profile"""
    name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    demographics = TextAreaField('Demographics (Address, Phone, Emergency Contact, etc.)')
    submit = SubmitField('Update Profile')

class PatientAppointmentForm(FlaskForm):
    """Form for patients to book appointments"""
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    datetime = DateTimeLocalField('Preferred Date & Time', validators=[DataRequired()])
    notes = TextAreaField('Reason for Visit')
    submit = SubmitField('Book Appointment')
    
    def __init__(self, *args, **kwargs):
        super(PatientAppointmentForm, self).__init__(*args, **kwargs)
        # Populate doctor choices
        self.doctor_id.choices = [(u.id, u.username) for u in User.query.filter(
            User.role.in_(['curing_doctor', 'special_doctor', 'chief_doctor'])
        ).all()]

# Search Forms
class SearchForm(FlaskForm):
    """Generic search form"""
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search') 