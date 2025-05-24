from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from app import db
from app.models import Patient, Appointment, MedicalRecord, User
from app.forms import PatientProfileForm, PatientAppointmentForm, SearchForm
from app.views.auth import role_required, log_action
from app.utils.encryption import decrypt_medical_record

bp = Blueprint('patient', __name__)

@bp.route('/dashboard')
@login_required
@role_required('patient')
def dashboard():
    """Patient dashboard with personal information and upcoming appointments"""
    try:
        # Get or create patient profile linked to user account
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        
        # Get upcoming appointments
        today = datetime.now().date()
        upcoming_appointments = Appointment.query.join(Patient).filter(
            db.and_(
                Patient.user_id == current_user.id,
                Appointment.datetime >= today,
                Appointment.status.in_(['scheduled', 'rescheduled'])
            )
        ).order_by(Appointment.datetime).limit(5).all()
        
        # Get recent medical records (limited view)
        recent_records = []
        if patient:
            records = MedicalRecord.query.filter_by(
                patient_id=patient.id
            ).order_by(MedicalRecord.timestamp.desc()).limit(5).all()
            
            # Decrypt and filter sensitive information
            for record in records:
                try:
                    decrypted_data = decrypt_medical_record(record.encrypted_blob, record.signature)
                    # Patient gets limited view - only basic info, no detailed medical data
                    limited_data = {
                        'record_type': decrypted_data.get('record_type', 'Unknown'),
                        'timestamp': decrypted_data.get('timestamp', ''),
                        'author': decrypted_data.get('author', 'Unknown'),
                        'chief_complaint': decrypted_data.get('chief_complaint', '')[:100] + '...' if len(decrypted_data.get('chief_complaint', '')) > 100 else decrypted_data.get('chief_complaint', ''),
                        # Hide sensitive medical details
                        'diagnosis': '[Medical details available on request]',
                        'treatment_plan': '[Treatment details available on request]'
                    }
                    recent_records.append({
                        'record': record,
                        'data': limited_data
                    })
                except Exception as e:
                    current_app.logger.error(f"Error decrypting record {record.id} for patient view: {str(e)}")
        
        # Summary statistics
        total_appointments = 0
        total_records = 0
        if patient:
            total_appointments = Appointment.query.filter_by(patient_id=patient.id).count()
            total_records = MedicalRecord.query.filter_by(patient_id=patient.id).count()
        
        return render_template('patient/dashboard.html',
                             patient=patient,
                             upcoming_appointments=upcoming_appointments,
                             recent_records=recent_records,
                             total_appointments=total_appointments,
                             total_records=total_records)
    except Exception as e:
        current_app.logger.error(f"Patient dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('patient/dashboard.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def complete_profile():
    """Complete or update patient profile"""
    try:
        # Get existing patient record or create new
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        
        form = PatientProfileForm()
        if patient:
            form = PatientProfileForm(obj=patient)
        
        if form.validate_on_submit():
            if patient:
                # Update existing profile
                old_values = {
                    'name': patient.name,
                    'date_of_birth': str(patient.date_of_birth),
                    'demographics': patient.demographics
                }
                
                patient.name = form.name.data
                patient.date_of_birth = form.date_of_birth.data
                patient.demographics = form.demographics.data
                
                action = 'UPDATE_PATIENT_PROFILE'
                message = 'Profile updated successfully.'
            else:
                # Create new profile
                patient = Patient(
                    name=form.name.data,
                    date_of_birth=form.date_of_birth.data,
                    demographics=form.demographics.data,
                    user_id=current_user.id
                )
                db.session.add(patient)
                old_values = None
                action = 'CREATE_PATIENT_PROFILE'
                message = 'Profile created successfully.'
            
            db.session.commit()
            
            # Log the action
            log_action(action, 'Patient', patient.id, {
                'old_values': old_values,
                'new_values': {
                    'name': patient.name,
                    'date_of_birth': str(patient.date_of_birth),
                    'demographics': patient.demographics
                }
            })
            
            flash(message, 'success')
            return redirect(url_for('patient.dashboard'))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Complete profile error: {str(e)}")
        flash('Error updating profile. Please try again.', 'error')
    
    return render_template('patient/profile_form.html', form=form, patient=patient)

@bp.route('/appointments')
@login_required
@role_required('patient')
def list_appointments():
    """View own appointments"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Please complete your profile first.', 'info')
            return redirect(url_for('patient.complete_profile'))
        
        # Get all appointments for this patient
        appointments = Appointment.query.filter_by(
            patient_id=patient.id
        ).order_by(Appointment.datetime.desc()).all()
        
        return render_template('patient/appointments.html',
                             appointments=appointments,
                             patient=patient)
    except Exception as e:
        current_app.logger.error(f"List appointments error: {str(e)}")
        flash('Error loading appointments.', 'error')
        return render_template('patient/appointments.html',
                             appointments=[],
                             patient=None)

@bp.route('/book-appointment', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def book_appointment():
    """Book a new appointment"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Please complete your profile first.', 'info')
            return redirect(url_for('patient.complete_profile'))
        
        form = PatientAppointmentForm()
        if form.validate_on_submit():
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=form.doctor_id.data,
                datetime=form.datetime.data,
                status='scheduled',
                notes=form.notes.data
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            # Log the action
            log_action('BOOK_APPOINTMENT', 'Appointment', appointment.id, {
                'patient_id': patient.id,
                'doctor_id': appointment.doctor_id,
                'datetime': str(appointment.datetime)
            })
            
            flash('Appointment booked successfully.', 'success')
            return redirect(url_for('patient.list_appointments'))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Book appointment error: {str(e)}")
        flash('Error booking appointment. Please try again.', 'error')
    
    return render_template('patient/appointment_form.html', form=form, title='Book Appointment')

@bp.route('/appointments/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@login_required
@role_required('patient')
def reschedule_appointment(appointment_id):
    """Reschedule an appointment"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Profile not found.', 'error')
            return redirect(url_for('patient.complete_profile'))
        
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            patient_id=patient.id
        ).first_or_404()
        
        # Only allow rescheduling future appointments
        if appointment.datetime < datetime.now():
            flash('Cannot reschedule past appointments.', 'error')
            return redirect(url_for('patient.list_appointments'))
        
        form = PatientAppointmentForm(obj=appointment)
        if form.validate_on_submit():
            old_datetime = appointment.datetime
            appointment.doctor_id = form.doctor_id.data
            appointment.datetime = form.datetime.data
            appointment.notes = form.notes.data
            appointment.status = 'rescheduled'
            
            db.session.commit()
            
            # Log the action
            log_action('RESCHEDULE_APPOINTMENT', 'Appointment', appointment.id, {
                'old_datetime': str(old_datetime),
                'new_datetime': str(appointment.datetime),
                'new_doctor_id': appointment.doctor_id
            })
            
            flash('Appointment rescheduled successfully.', 'success')
            return redirect(url_for('patient.list_appointments'))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reschedule appointment error: {str(e)}")
        flash('Error rescheduling appointment. Please try again.', 'error')
    
    return render_template('patient/appointment_form.html', 
                         form=form, title='Reschedule Appointment', appointment=appointment)

@bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@role_required('patient')
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Profile not found.', 'error')
            return redirect(url_for('patient.complete_profile'))
        
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            patient_id=patient.id
        ).first_or_404()
        
        # Only allow cancelling future appointments
        if appointment.datetime < datetime.now():
            flash('Cannot cancel past appointments.', 'error')
            return redirect(url_for('patient.list_appointments'))
        
        old_status = appointment.status
        appointment.status = 'cancelled'
        
        db.session.commit()
        
        # Log the action
        log_action('CANCEL_APPOINTMENT', 'Appointment', appointment.id, {
            'old_status': old_status,
            'datetime': str(appointment.datetime)
        })
        
        flash('Appointment cancelled successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel appointment error: {str(e)}")
        flash('Error cancelling appointment. Please try again.', 'error')
    
    return redirect(url_for('patient.list_appointments'))

@bp.route('/medical-records')
@login_required
@role_required('patient')
def view_medical_records():
    """View partial (non-sensitive) sections of own medical records"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Please complete your profile first.', 'info')
            return redirect(url_for('patient.complete_profile'))
        
        # Get medical records for this patient
        medical_records = MedicalRecord.query.filter_by(
            patient_id=patient.id
        ).order_by(MedicalRecord.timestamp.desc()).all()
        
        # Decrypt records and provide limited view
        limited_records = []
        for record in medical_records:
            try:
                decrypted_data = decrypt_medical_record(record.encrypted_blob, record.signature)
                # Patient gets limited view - basic info only
                limited_data = {
                    'record_type': decrypted_data.get('record_type', 'Unknown'),
                    'timestamp': decrypted_data.get('timestamp', ''),
                    'author': decrypted_data.get('author', 'Unknown'),
                    'chief_complaint': decrypted_data.get('chief_complaint', ''),
                    'visit_summary': f"Visit on {record.timestamp.strftime('%Y-%m-%d')} for {decrypted_data.get('record_type', 'medical care')}",
                    # Hide detailed medical information
                    'note': 'For complete medical details, please contact your healthcare provider.'
                }
                limited_records.append({
                    'record': record,
                    'data': limited_data
                })
            except Exception as e:
                current_app.logger.error(f"Error decrypting record {record.id} for patient view: {str(e)}")
                limited_records.append({
                    'record': record,
                    'data': {'error': 'Unable to display record details'}
                })
        
        return render_template('patient/medical_records.html',
                             limited_records=limited_records,
                             patient=patient)
    except Exception as e:
        current_app.logger.error(f"View medical records error: {str(e)}")
        flash('Error loading medical records.', 'error')
        return render_template('patient/medical_records.html',
                             limited_records=[],
                             patient=None)

@bp.route('/visit-summary/<int:record_id>/download')
@login_required
@role_required('patient')
def download_visit_summary(record_id):
    """Download visit summary as PDF"""
    try:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Profile not found.', 'error')
            return redirect(url_for('patient.complete_profile'))
        
        medical_record = MedicalRecord.query.filter_by(
            id=record_id,
            patient_id=patient.id
        ).first_or_404()
        
        # Decrypt record
        decrypted_data = decrypt_medical_record(medical_record.encrypted_blob, medical_record.signature)
        
        # Create PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add content to PDF
        y = height - 50
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, "Visit Summary")
        
        y -= 30
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"Patient: {patient.name}")
        
        y -= 20
        p.drawString(50, y, f"Date: {medical_record.timestamp.strftime('%Y-%m-%d')}")
        
        y -= 20
        p.drawString(50, y, f"Doctor: {decrypted_data.get('author', 'Unknown')}")
        
        y -= 20
        p.drawString(50, y, f"Visit Type: {decrypted_data.get('record_type', 'Unknown')}")
        
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Chief Complaint:")
        
        y -= 20
        p.setFont("Helvetica", 10)
        complaint = decrypted_data.get('chief_complaint', 'Not specified')
        # Wrap text
        words = complaint.split(' ')
        line = ""
        for word in words:
            if len(line + word) < 80:
                line += word + " "
            else:
                p.drawString(50, y, line)
                y -= 15
                line = word + " "
        if line:
            p.drawString(50, y, line)
        
        y -= 30
        p.setFont("Helvetica", 10)
        p.drawString(50, y, "For complete medical details, please contact your healthcare provider.")
        
        y -= 30
        p.drawString(50, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        p.save()
        buffer.seek(0)
        
        # Log the action
        log_action('DOWNLOAD_VISIT_SUMMARY', 'MedicalRecord', record_id, {
            'patient_id': patient.id,
            'record_type': decrypted_data.get('record_type', 'Unknown')
        })
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=visit_summary_{record_id}.pdf'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Download visit summary error: {str(e)}")
        flash('Error generating visit summary. Please try again.', 'error')
        return redirect(url_for('patient.view_medical_records'))

# TODO: Students can extend this section with additional patient functionality:
# - Online bill payment
# - Insurance information management
# - Prescription refill requests
# - Health tracking and monitoring
# - Telemedicine appointments 