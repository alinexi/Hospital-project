from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Patient, Appointment, User
from app.forms import PatientForm, AppointmentForm, SearchForm
from app.views.auth import role_required, log_action

bp = Blueprint('receptionist', __name__)

@bp.route('/dashboard')
@login_required
@role_required('receptionist')
def dashboard():
    """Receptionist dashboard with today's appointments and recent patients"""
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Today's appointments
        todays_appointments = Appointment.query.filter(
            db.and_(
                Appointment.datetime >= today,
                Appointment.datetime < tomorrow
            )
        ).order_by(Appointment.datetime).all()
        
        # Recent patients (last 10)
        recent_patients = Patient.query.order_by(Patient.id.desc()).limit(10).all()
        
        # Summary statistics
        total_patients = Patient.query.count()
        total_appointments_today = len(todays_appointments)
        pending_appointments = Appointment.query.filter_by(status='scheduled').count()
        
        return render_template('receptionist/dashboard.html',
                             todays_appointments=todays_appointments,
                             recent_patients=recent_patients,
                             total_patients=total_patients,
                             total_appointments_today=total_appointments_today,
                             pending_appointments=pending_appointments)
    except Exception as e:
        current_app.logger.error(f"Receptionist dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('receptionist/dashboard.html')

@bp.route('/patients')
@login_required
@role_required('receptionist')
def list_patients():
    """List and search patients"""
    try:
        search_form = SearchForm()
        patients = Patient.query.order_by(Patient.name).all()
        
        if search_form.validate_on_submit():
            query = search_form.query.data
            patients = Patient.query.filter(
                db.or_(
                    Patient.name.contains(query),
                    Patient.demographics.contains(query)
                )
            ).order_by(Patient.name).all()
        
        return render_template('receptionist/patients.html', 
                             patients=patients, 
                             search_form=search_form)
    except Exception as e:
        current_app.logger.error(f"List patients error: {str(e)}")
        flash('Error loading patients.', 'error')
        return render_template('receptionist/patients.html', 
                             patients=[], 
                             search_form=SearchForm())

@bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def register_patient():
    """Register a new patient"""
    form = PatientForm()
    if form.validate_on_submit():
        try:
            patient = Patient(
                name=form.name.data,
                date_of_birth=form.date_of_birth.data,
                demographics=form.demographics.data
            )
            db.session.add(patient)
            db.session.commit()
            
            # Log the action
            log_action('REGISTER_PATIENT', 'Patient', patient.id, {
                'name': patient.name,
                'date_of_birth': str(patient.date_of_birth)
            })
            
            flash(f'Patient {patient.name} registered successfully.', 'success')
            return redirect(url_for('receptionist.list_patients'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Register patient error: {str(e)}")
            flash('Error registering patient. Please try again.', 'error')
    
    return render_template('receptionist/patient_form.html', form=form, title='Register Patient')

@bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def edit_patient(patient_id):
    """Update patient demographics"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        form = PatientForm(obj=patient)
        
        if form.validate_on_submit():
            # Store old values for audit log
            old_values = {
                'name': patient.name,
                'date_of_birth': str(patient.date_of_birth),
                'demographics': patient.demographics
            }
            
            patient.name = form.name.data
            patient.date_of_birth = form.date_of_birth.data
            patient.demographics = form.demographics.data
            
            db.session.commit()
            
            # Log the action
            new_values = {
                'name': patient.name,
                'date_of_birth': str(patient.date_of_birth),
                'demographics': patient.demographics
            }
            log_action('UPDATE_PATIENT', 'Patient', patient.id, {
                'old_values': old_values,
                'new_values': new_values
            })
            
            flash(f'Patient {patient.name} updated successfully.', 'success')
            return redirect(url_for('receptionist.list_patients'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit patient error: {str(e)}")
        flash('Error updating patient. Please try again.', 'error')
    
    return render_template('receptionist/patient_form.html', 
                         form=form, title='Edit Patient', patient=patient)

@bp.route('/appointments')
@login_required
@role_required('receptionist')
def list_appointments():
    """View appointment calendar"""
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
                Appointment.datetime >= filter_date,
                Appointment.datetime < next_day
            )
        ).order_by(Appointment.datetime).all()
        
        return render_template('receptionist/appointments.html', 
                             appointments=appointments,
                             selected_date=filter_date)
    except Exception as e:
        current_app.logger.error(f"List appointments error: {str(e)}")
        flash('Error loading appointments.', 'error')
        return render_template('receptionist/appointments.html', 
                             appointments=[],
                             selected_date=datetime.now().date())

@bp.route('/appointments/schedule', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def schedule_appointment():
    """Schedule a new appointment"""
    form = AppointmentForm()
    if form.validate_on_submit():
        try:
            appointment = Appointment(
                patient_id=form.patient_id.data,
                doctor_id=form.doctor_id.data,
                datetime=form.datetime.data,
                status=form.status.data,
                notes=form.notes.data
            )
            db.session.add(appointment)
            db.session.commit()
            
            # Log the action
            log_action('SCHEDULE_APPOINTMENT', 'Appointment', appointment.id, {
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'datetime': str(appointment.datetime),
                'status': appointment.status
            })
            
            flash('Appointment scheduled successfully.', 'success')
            return redirect(url_for('receptionist.list_appointments'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Schedule appointment error: {str(e)}")
            flash('Error scheduling appointment. Please try again.', 'error')
    
    return render_template('receptionist/appointment_form.html', 
                         form=form, title='Schedule Appointment')

@bp.route('/appointments/<int:appointment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def edit_appointment(appointment_id):
    """Reschedule or update appointment"""
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        form = AppointmentForm(obj=appointment)
        
        if form.validate_on_submit():
            # Store old values for audit log
            old_values = {
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'datetime': str(appointment.datetime),
                'status': appointment.status,
                'notes': appointment.notes
            }
            
            appointment.patient_id = form.patient_id.data
            appointment.doctor_id = form.doctor_id.data
            appointment.datetime = form.datetime.data
            appointment.status = form.status.data
            appointment.notes = form.notes.data
            
            db.session.commit()
            
            # Log the action
            new_values = {
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'datetime': str(appointment.datetime),
                'status': appointment.status,
                'notes': appointment.notes
            }
            log_action('UPDATE_APPOINTMENT', 'Appointment', appointment.id, {
                'old_values': old_values,
                'new_values': new_values
            })
            
            flash('Appointment updated successfully.', 'success')
            return redirect(url_for('receptionist.list_appointments'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Edit appointment error: {str(e)}")
        flash('Error updating appointment. Please try again.', 'error')
    
    return render_template('receptionist/appointment_form.html', 
                         form=form, title='Edit Appointment', appointment=appointment)

@bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@role_required('receptionist')
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        
        old_status = appointment.status
        appointment.status = 'cancelled'
        
        db.session.commit()
        
        # Log the action
        log_action('CANCEL_APPOINTMENT', 'Appointment', appointment.id, {
            'old_status': old_status,
            'new_status': 'cancelled'
        })
        
        flash('Appointment cancelled successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cancel appointment error: {str(e)}")
        flash('Error cancelling appointment. Please try again.', 'error')
    
    return redirect(url_for('receptionist.list_appointments'))

# TODO: Students can extend this section with additional receptionist functionality:
# - Patient check-in/check-out
# - Appointment reminders
# - Waiting room management
# - Insurance verification
# - Billing integration 