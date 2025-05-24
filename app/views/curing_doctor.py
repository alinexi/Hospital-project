from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Patient, Appointment, MedicalRecord, AccessGrant, PatientAssignment
from app.forms import MedicalRecordForm, AccessGrantForm, SearchForm
from app.views.auth import role_required, log_action
from app.utils.encryption import encrypt_medical_record, decrypt_medical_record

bp = Blueprint('curing_doctor', __name__)

@bp.route('/dashboard')
@login_required
@role_required('curing_doctor')
def dashboard():
    """Curing doctor dashboard with assigned patients and appointments"""
    try:
        # Get assigned patients
        assigned_patients = db.session.query(Patient).join(PatientAssignment).filter(
            PatientAssignment.doctor_id == current_user.id
        ).all()
        
        # Get today's appointments
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        todays_appointments = Appointment.query.filter(
            db.and_(
                Appointment.doctor_id == current_user.id,
                Appointment.datetime >= today,
                Appointment.datetime < tomorrow
            )
        ).order_by(Appointment.datetime).all()
        
        # Recent medical records authored by this doctor
        recent_records = MedicalRecord.query.filter_by(
            author_id=current_user.id
        ).order_by(MedicalRecord.timestamp.desc()).limit(5).all()
        
        # Summary statistics
        total_assigned_patients = len(assigned_patients)
        total_appointments_today = len(todays_appointments)
        total_records_authored = MedicalRecord.query.filter_by(author_id=current_user.id).count()
        
        return render_template('curing_doctor/dashboard.html',
                             assigned_patients=assigned_patients,
                             todays_appointments=todays_appointments,
                             recent_records=recent_records,
                             total_assigned_patients=total_assigned_patients,
                             total_appointments_today=total_appointments_today,
                             total_records_authored=total_records_authored)
    except Exception as e:
        current_app.logger.error(f"Curing doctor dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('curing_doctor/dashboard.html')

@bp.route('/patients')
@login_required
@role_required('curing_doctor')
def list_patients():
    """List assigned patients"""
    try:
        # Get patients assigned to this doctor
        assigned_patients = db.session.query(Patient).join(PatientAssignment).filter(
            PatientAssignment.doctor_id == current_user.id
        ).order_by(Patient.name).all()
        
        return render_template('curing_doctor/patients.html', patients=assigned_patients)
    except Exception as e:
        current_app.logger.error(f"List patients error: {str(e)}")
        flash('Error loading patients.', 'error')
        return render_template('curing_doctor/patients.html', patients=[])

@bp.route('/patients/<int:patient_id>/records')
@login_required
@role_required('curing_doctor')
def patient_records(patient_id):
    """View medical records for a specific patient"""
    try:
        # Check if patient is assigned to this doctor
        assignment = PatientAssignment.query.filter_by(
            patient_id=patient_id,
            doctor_id=current_user.id
        ).first()
        
        if not assignment:
            flash('Access denied. Patient not assigned to you.', 'error')
            return redirect(url_for('curing_doctor.list_patients'))
        
        patient = Patient.query.get_or_404(patient_id)
        medical_records = MedicalRecord.query.filter_by(
            patient_id=patient_id
        ).order_by(MedicalRecord.timestamp.desc()).all()
        
        # Decrypt records for display
        decrypted_records = []
        for record in medical_records:
            try:
                decrypted_data = decrypt_medical_record(record.encrypted_blob, record.signature)
                decrypted_records.append({
                    'record': record,
                    'data': decrypted_data
                })
            except Exception as e:
                current_app.logger.error(f"Error decrypting record {record.id}: {str(e)}")
                decrypted_records.append({
                    'record': record,
                    'data': {'error': 'Failed to decrypt record'}
                })
        
        return render_template('curing_doctor/patient_records.html',
                             patient=patient,
                             decrypted_records=decrypted_records)
    except Exception as e:
        current_app.logger.error(f"Patient records error: {str(e)}")
        flash('Error loading medical records.', 'error')
        return redirect(url_for('curing_doctor.list_patients'))

@bp.route('/patients/<int:patient_id>/records/create', methods=['GET', 'POST'])
@login_required
@role_required('curing_doctor')
def create_medical_record(patient_id):
    """Create a new medical record"""
    try:
        # Check if patient is assigned to this doctor
        assignment = PatientAssignment.query.filter_by(
            patient_id=patient_id,
            doctor_id=current_user.id
        ).first()
        
        if not assignment:
            flash('Access denied. Patient not assigned to you.', 'error')
            return redirect(url_for('curing_doctor.list_patients'))
        
        patient = Patient.query.get_or_404(patient_id)
        form = MedicalRecordForm()
        form.patient_id.data = patient_id
        form.patient_id.choices = [(patient.id, patient.name)]
        
        if form.validate_on_submit():
            # Prepare medical record data for encryption
            record_data = {
                'record_type': form.record_type.data,
                'chief_complaint': form.chief_complaint.data,
                'history_present_illness': form.history_present_illness.data,
                'physical_examination': form.physical_examination.data,
                'diagnosis': form.diagnosis.data,
                'treatment_plan': form.treatment_plan.data,
                'medications': form.medications.data,
                'lab_results': form.lab_results.data,
                'notes': form.notes.data,
                'author': current_user.username,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Encrypt and sign the medical record
            encrypted_blob, signature = encrypt_medical_record(record_data)
            
            medical_record = MedicalRecord(
                patient_id=patient_id,
                author_id=current_user.id,
                encrypted_blob=encrypted_blob,
                signature=signature,
                record_type=form.record_type.data
            )
            
            db.session.add(medical_record)
            db.session.commit()
            
            # Log the action
            log_action('CREATE_MEDICAL_RECORD', 'MedicalRecord', medical_record.id, {
                'patient_id': patient_id,
                'record_type': form.record_type.data
            })
            
            flash('Medical record created successfully.', 'success')
            return redirect(url_for('curing_doctor.patient_records', patient_id=patient_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create medical record error: {str(e)}")
        flash('Error creating medical record. Please try again.', 'error')
    
    return render_template('curing_doctor/medical_record_form.html',
                         form=form, title='Create Medical Record', patient=patient)

@bp.route('/records/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('curing_doctor')
def edit_medical_record(record_id):
    """Edit an existing medical record"""
    try:
        medical_record = MedicalRecord.query.get_or_404(record_id)
        
        # Check if record belongs to assigned patient and authored by this doctor
        assignment = PatientAssignment.query.filter_by(
            patient_id=medical_record.patient_id,
            doctor_id=current_user.id
        ).first()
        
        if not assignment or medical_record.author_id != current_user.id:
            flash('Access denied. You can only edit your own records for assigned patients.', 'error')
            return redirect(url_for('curing_doctor.list_patients'))
        
        # Decrypt existing record data
        decrypted_data = decrypt_medical_record(medical_record.encrypted_blob, medical_record.signature)
        
        form = MedicalRecordForm()
        form.patient_id.data = medical_record.patient_id
        form.patient_id.choices = [(medical_record.patient.id, medical_record.patient.name)]
        
        if request.method == 'GET':
            # Populate form with decrypted data
            form.record_type.data = decrypted_data.get('record_type', medical_record.record_type)
            form.chief_complaint.data = decrypted_data.get('chief_complaint', '')
            form.history_present_illness.data = decrypted_data.get('history_present_illness', '')
            form.physical_examination.data = decrypted_data.get('physical_examination', '')
            form.diagnosis.data = decrypted_data.get('diagnosis', '')
            form.treatment_plan.data = decrypted_data.get('treatment_plan', '')
            form.medications.data = decrypted_data.get('medications', '')
            form.lab_results.data = decrypted_data.get('lab_results', '')
            form.notes.data = decrypted_data.get('notes', '')
        
        if form.validate_on_submit():
            # Prepare updated medical record data for encryption
            record_data = {
                'record_type': form.record_type.data,
                'chief_complaint': form.chief_complaint.data,
                'history_present_illness': form.history_present_illness.data,
                'physical_examination': form.physical_examination.data,
                'diagnosis': form.diagnosis.data,
                'treatment_plan': form.treatment_plan.data,
                'medications': form.medications.data,
                'lab_results': form.lab_results.data,
                'notes': form.notes.data,
                'author': current_user.username,
                'original_timestamp': decrypted_data.get('timestamp'),
                'last_modified': datetime.utcnow().isoformat()
            }
            
            # Encrypt and sign the updated medical record
            encrypted_blob, signature = encrypt_medical_record(record_data)
            
            medical_record.encrypted_blob = encrypted_blob
            medical_record.signature = signature
            medical_record.record_type = form.record_type.data
            medical_record.timestamp = datetime.utcnow()
            
            db.session.commit()
            
            # Log the action
            log_action('UPDATE_MEDICAL_RECORD', 'MedicalRecord', medical_record.id, {
                'patient_id': medical_record.patient_id,
                'record_type': form.record_type.data
            })
            
            flash('Medical record updated successfully.', 'success')
            return redirect(url_for('curing_doctor.patient_records', patient_id=medical_record.patient_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit medical record error: {str(e)}")
        flash('Error updating medical record. Please try again.', 'error')
        return redirect(url_for('curing_doctor.list_patients'))
    
    return render_template('curing_doctor/medical_record_form.html',
                         form=form, title='Edit Medical Record', 
                         record=medical_record, patient=medical_record.patient)

@bp.route('/records/<int:record_id>/delete', methods=['POST'])
@login_required
@role_required('curing_doctor')
def delete_medical_record(record_id):
    """Delete a medical record"""
    try:
        medical_record = MedicalRecord.query.get_or_404(record_id)
        
        # Check if record belongs to assigned patient and authored by this doctor
        assignment = PatientAssignment.query.filter_by(
            patient_id=medical_record.patient_id,
            doctor_id=current_user.id
        ).first()
        
        if not assignment or medical_record.author_id != current_user.id:
            flash('Access denied. You can only delete your own records for assigned patients.', 'error')
            return redirect(url_for('curing_doctor.list_patients'))
        
        patient_id = medical_record.patient_id
        
        # Log before deletion
        log_action('DELETE_MEDICAL_RECORD', 'MedicalRecord', medical_record.id, {
            'patient_id': medical_record.patient_id,
            'record_type': medical_record.record_type
        })
        
        db.session.delete(medical_record)
        db.session.commit()
        
        flash('Medical record deleted successfully.', 'success')
        return redirect(url_for('curing_doctor.patient_records', patient_id=patient_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete medical record error: {str(e)}")
        flash('Error deleting medical record. Please try again.', 'error')
        return redirect(url_for('curing_doctor.list_patients'))

@bp.route('/records/<int:record_id>/grant-access', methods=['GET', 'POST'])
@login_required
@role_required('curing_doctor')
def grant_access(record_id):
    """Grant read access to special doctors"""
    try:
        medical_record = MedicalRecord.query.get_or_404(record_id)
        
        # Check if record belongs to assigned patient and authored by this doctor
        assignment = PatientAssignment.query.filter_by(
            patient_id=medical_record.patient_id,
            doctor_id=current_user.id
        ).first()
        
        if not assignment or medical_record.author_id != current_user.id:
            flash('Access denied. You can only grant access to your own records.', 'error')
            return redirect(url_for('curing_doctor.list_patients'))
        
        form = AccessGrantForm()
        form.record_id.data = record_id
        
        if form.validate_on_submit():
            # Check if access already granted
            existing_grant = AccessGrant.query.filter_by(
                record_id=record_id,
                granted_to_user_id=form.special_doctor_id.data
            ).first()
            
            if existing_grant:
                flash('Access already granted to this doctor.', 'info')
                return redirect(url_for('curing_doctor.patient_records', patient_id=medical_record.patient_id))
            
            access_grant = AccessGrant(
                record_id=record_id,
                granted_to_user_id=form.special_doctor_id.data,
                granted_by_user_id=current_user.id
            )
            
            db.session.add(access_grant)
            db.session.commit()
            
            # Log the action
            log_action('GRANT_RECORD_ACCESS', 'AccessGrant', access_grant.id, {
                'record_id': record_id,
                'granted_to_user_id': form.special_doctor_id.data
            })
            
            flash('Access granted successfully.', 'success')
            return redirect(url_for('curing_doctor.patient_records', patient_id=medical_record.patient_id))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Grant access error: {str(e)}")
        flash('Error granting access. Please try again.', 'error')
    
    return render_template('curing_doctor/grant_access_form.html',
                         form=form, record=medical_record)

@bp.route('/appointments')
@login_required
@role_required('curing_doctor')
def list_appointments():
    """View and manage own appointment schedule"""
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
        
        return render_template('curing_doctor/appointments.html',
                             appointments=appointments,
                             selected_date=filter_date)
    except Exception as e:
        current_app.logger.error(f"List appointments error: {str(e)}")
        flash('Error loading appointments.', 'error')
        return render_template('curing_doctor/appointments.html',
                             appointments=[],
                             selected_date=datetime.now().date())

# TODO: Students can extend this section with additional curing doctor functionality:
# - Treatment plan templates
# - Prescription management
# - Lab order integration
# - Patient communication
# - Outcome tracking 