from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Patient, Appointment, MedicalRecord, AccessGrant
from app.forms import SearchForm
from app.views.auth import role_required, log_action
from app.utils.encryption import decrypt_medical_record

bp = Blueprint('special_doctor', __name__)

@bp.route('/dashboard')
@login_required
@role_required('special_doctor')
def dashboard():
    """Special doctor dashboard with granted records and consulting appointments"""
    try:
        # Get records with granted access
        granted_records = db.session.query(MedicalRecord).join(AccessGrant).filter(
            AccessGrant.granted_to_user_id == current_user.id
        ).order_by(MedicalRecord.timestamp.desc()).limit(10).all()
        
        # Get today's consulting appointments
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        todays_appointments = Appointment.query.filter(
            db.and_(
                Appointment.doctor_id == current_user.id,
                Appointment.datetime >= today,
                Appointment.datetime < tomorrow
            )
        ).order_by(Appointment.datetime).all()
        
        # Get patients for whom this doctor has been granted access
        granted_patients = db.session.query(Patient).join(
            MedicalRecord, Patient.id == MedicalRecord.patient_id
        ).join(AccessGrant).filter(
            AccessGrant.granted_to_user_id == current_user.id
        ).distinct().order_by(Patient.name).all()
        
        # Summary statistics
        total_granted_records = db.session.query(MedicalRecord).join(AccessGrant).filter(
            AccessGrant.granted_to_user_id == current_user.id
        ).count()
        
        total_consulting_patients = len(granted_patients)
        total_appointments_today = len(todays_appointments)
        
        return render_template('special_doctor/dashboard.html',
                             granted_records=granted_records,
                             todays_appointments=todays_appointments,
                             granted_patients=granted_patients,
                             total_granted_records=total_granted_records,
                             total_consulting_patients=total_consulting_patients,
                             total_appointments_today=total_appointments_today)
    except Exception as e:
        current_app.logger.error(f"Special doctor dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('special_doctor/dashboard.html')

@bp.route('/granted-records')
@login_required
@role_required('special_doctor')
def list_granted_records():
    """View read-only medical records for granted patients"""
    try:
        search_form = SearchForm()
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Base query for records with granted access
        query = db.session.query(MedicalRecord).join(AccessGrant).join(
            Patient, MedicalRecord.patient_id == Patient.id
        ).filter(AccessGrant.granted_to_user_id == current_user.id)
        
        # Apply search filter if provided
        if search_form.validate_on_submit():
            search_term = search_form.query.data
            query = query.filter(
                db.or_(
                    Patient.name.contains(search_term),
                    MedicalRecord.record_type.contains(search_term)
                )
            )
        
        # Paginate results
        medical_records = query.order_by(MedicalRecord.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('special_doctor/granted_records.html',
                             medical_records=medical_records,
                             search_form=search_form)
    except Exception as e:
        current_app.logger.error(f"List granted records error: {str(e)}")
        flash('Error loading granted records.', 'error')
        return render_template('special_doctor/granted_records.html',
                             medical_records=None,
                             search_form=SearchForm())

@bp.route('/granted-records/<int:record_id>')
@login_required
@role_required('special_doctor')
def view_granted_record(record_id):
    """View details of a granted medical record (read-only)"""
    try:
        # Check if access is granted for this record
        access_grant = AccessGrant.query.filter_by(
            record_id=record_id,
            granted_to_user_id=current_user.id
        ).first()
        
        if not access_grant:
            flash('Access denied. You do not have permission to view this record.', 'error')
            return redirect(url_for('special_doctor.list_granted_records'))
        
        medical_record = MedicalRecord.query.get_or_404(record_id)
        
        # Decrypt record for viewing
        try:
            decrypted_data = decrypt_medical_record(medical_record.encrypted_blob, medical_record.signature)
        except Exception as e:
            current_app.logger.error(f"Error decrypting record {record_id}: {str(e)}")
            flash('Error decrypting medical record. Record may be corrupted.', 'error')
            decrypted_data = {'error': 'Failed to decrypt record'}
        
        # Log access for audit trail
        log_action('VIEW_GRANTED_RECORD', 'MedicalRecord', record_id, {
            'patient_id': medical_record.patient_id,
            'access_grant_id': access_grant.id
        })
        
        return render_template('special_doctor/granted_record_detail.html',
                             record=medical_record,
                             decrypted_data=decrypted_data,
                             access_grant=access_grant)
    except Exception as e:
        current_app.logger.error(f"View granted record error: {str(e)}")
        flash('Error loading medical record.', 'error')
        return redirect(url_for('special_doctor.list_granted_records'))

@bp.route('/consulting-assignments')
@login_required
@role_required('special_doctor')
def list_consulting_assignments():
    """List consulting assignments (patients with granted access)"""
    try:
        # Get patients for whom this doctor has been granted access
        # Group by patient to show all granted records per patient
        granted_access_query = db.session.query(
            Patient.id,
            Patient.name,
            Patient.date_of_birth,
            db.func.count(AccessGrant.id).label('granted_records_count'),
            db.func.max(AccessGrant.granted_date).label('latest_grant_date')
        ).join(
            MedicalRecord, Patient.id == MedicalRecord.patient_id
        ).join(AccessGrant).filter(
            AccessGrant.granted_to_user_id == current_user.id
        ).group_by(Patient.id, Patient.name, Patient.date_of_birth).all()
        
        # Convert to list of dictionaries for easier template handling
        consulting_assignments = []
        for assignment in granted_access_query:
            patient = Patient.query.get(assignment.id)
            consulting_assignments.append({
                'patient': patient,
                'granted_records_count': assignment.granted_records_count,
                'latest_grant_date': assignment.latest_grant_date
            })
        
        return render_template('special_doctor/consulting_assignments.html',
                             consulting_assignments=consulting_assignments)
    except Exception as e:
        current_app.logger.error(f"List consulting assignments error: {str(e)}")
        flash('Error loading consulting assignments.', 'error')
        return render_template('special_doctor/consulting_assignments.html',
                             consulting_assignments=[])

@bp.route('/patient/<int:patient_id>/granted-records')
@login_required
@role_required('special_doctor')
def patient_granted_records(patient_id):
    """View all granted records for a specific patient"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Get all records for this patient that have been granted to this doctor
        granted_records = db.session.query(MedicalRecord).join(AccessGrant).filter(
            db.and_(
                MedicalRecord.patient_id == patient_id,
                AccessGrant.granted_to_user_id == current_user.id
            )
        ).order_by(MedicalRecord.timestamp.desc()).all()
        
        if not granted_records:
            flash('No granted records found for this patient.', 'error')
            return redirect(url_for('special_doctor.list_consulting_assignments'))
        
        # Decrypt records for display
        decrypted_records = []
        for record in granted_records:
            try:
                decrypted_data = decrypt_medical_record(record.encrypted_blob, record.signature)
                access_grant = AccessGrant.query.filter_by(
                    record_id=record.id,
                    granted_to_user_id=current_user.id
                ).first()
                decrypted_records.append({
                    'record': record,
                    'data': decrypted_data,
                    'access_grant': access_grant
                })
            except Exception as e:
                current_app.logger.error(f"Error decrypting record {record.id}: {str(e)}")
                decrypted_records.append({
                    'record': record,
                    'data': {'error': 'Failed to decrypt record'},
                    'access_grant': None
                })
        
        return render_template('special_doctor/patient_granted_records.html',
                             patient=patient,
                             decrypted_records=decrypted_records)
    except Exception as e:
        current_app.logger.error(f"Patient granted records error: {str(e)}")
        flash('Error loading patient records.', 'error')
        return redirect(url_for('special_doctor.list_consulting_assignments'))

@bp.route('/appointments')
@login_required
@role_required('special_doctor')
def list_appointments():
    """View consulting appointment schedule"""
    try:
        # Get date filter from query params
        date_str = request.args.get('date')
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                filter_date = datetime.now().date()
        else:
            filter_date = datetime.now().date()
        
        # Get appointments for the selected date
        next_day = filter_date + timedelta(days=1)
        appointments = Appointment.query.filter(
            db.and_(
                Appointment.doctor_id == current_user.id,
                Appointment.datetime >= filter_date,
                Appointment.datetime < next_day
            )
        ).order_by(Appointment.datetime).all()
        
        return render_template('special_doctor/appointments.html',
                             appointments=appointments,
                             selected_date=filter_date)
    except Exception as e:
        current_app.logger.error(f"List appointments error: {str(e)}")
        flash('Error loading appointments.', 'error')
        return render_template('special_doctor/appointments.html',
                             appointments=[],
                             selected_date=datetime.now().date())

@bp.route('/access-grants')
@login_required
@role_required('special_doctor')
def list_access_grants():
    """View all access grants received"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get all access grants for this doctor
        access_grants = db.session.query(AccessGrant).join(
            MedicalRecord, AccessGrant.record_id == MedicalRecord.id
        ).join(
            Patient, MedicalRecord.patient_id == Patient.id
        ).filter(
            AccessGrant.granted_to_user_id == current_user.id
        ).order_by(AccessGrant.granted_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('special_doctor/access_grants.html',
                             access_grants=access_grants)
    except Exception as e:
        current_app.logger.error(f"List access grants error: {str(e)}")
        flash('Error loading access grants.', 'error')
        return render_template('special_doctor/access_grants.html',
                             access_grants=None)

# TODO: Students can extend this section with additional special doctor functionality:
# - Consultation notes and recommendations
# - Second opinion documentation
# - Inter-doctor communication
# - Specialist referral tracking
# - Consultation reports 