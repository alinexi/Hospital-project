from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Patient, Appointment, MedicalRecord, User, PatientAssignment
from app.forms import PatientAssignmentForm, SearchForm
from app.views.auth import role_required, log_action
from app.utils.encryption import decrypt_medical_record

bp = Blueprint('chief_doctor', __name__)

@bp.route('/dashboard')
@login_required
@role_required('chief_doctor')
def dashboard():
    """Chief doctor dashboard with overview statistics and reports"""
    try:
        # Summary statistics
        total_patients = Patient.query.count()
        total_doctors = User.query.filter(User.role.in_(['curing_doctor', 'special_doctor'])).count()
        total_records = MedicalRecord.query.count()
        
        # Today's appointments across all doctors
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        todays_appointments = Appointment.query.filter(
            db.and_(
                Appointment.datetime >= today,
                Appointment.datetime < tomorrow
            )
        ).count()
        
        # Upcoming appointments (next 7 days)
        next_week = today + timedelta(days=7)
        upcoming_appointments = Appointment.query.filter(
            db.and_(
                Appointment.datetime >= today,
                Appointment.datetime < next_week,
                Appointment.status == 'scheduled'
            )
        ).order_by(Appointment.datetime).limit(10).all()
        
        # Patient assignment statistics
        assigned_patients = PatientAssignment.query.count()
        unassigned_patients = Patient.query.outerjoin(PatientAssignment).filter(
            PatientAssignment.patient_id.is_(None)
        ).count()
        
        # Doctor workload
        doctor_workloads = db.session.query(
            User.username,
            db.func.count(PatientAssignment.patient_id).label('patient_count')
        ).outerjoin(PatientAssignment, User.id == PatientAssignment.doctor_id).filter(
            User.role == 'curing_doctor'
        ).group_by(User.id, User.username).all()
        
        return render_template('chief_doctor/dashboard.html',
                             total_patients=total_patients,
                             total_doctors=total_doctors,
                             total_records=total_records,
                             todays_appointments=todays_appointments,
                             upcoming_appointments=upcoming_appointments,
                             assigned_patients=assigned_patients,
                             unassigned_patients=unassigned_patients,
                             doctor_workloads=doctor_workloads)
    except Exception as e:
        current_app.logger.error(f"Chief doctor dashboard error: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('chief_doctor/dashboard.html')

@bp.route('/medical-records')
@login_required
@role_required('chief_doctor')
def list_medical_records():
    """View read-only lists of all medical records"""
    try:
        search_form = SearchForm()
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Base query for all medical records
        query = db.session.query(MedicalRecord).join(Patient).join(
            User, MedicalRecord.author_id == User.id
        )
        
        # Apply search filter if provided
        if search_form.validate_on_submit():
            search_term = search_form.query.data
            query = query.filter(
                db.or_(
                    Patient.name.contains(search_term),
                    User.username.contains(search_term),
                    MedicalRecord.record_type.contains(search_term)
                )
            )
        
        # Paginate results
        medical_records = query.order_by(MedicalRecord.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('chief_doctor/medical_records.html',
                             medical_records=medical_records,
                             search_form=search_form)
    except Exception as e:
        current_app.logger.error(f"List medical records error: {str(e)}")
        flash('Error loading medical records.', 'error')
        return render_template('chief_doctor/medical_records.html',
                             medical_records=None,
                             search_form=SearchForm())

@bp.route('/medical-records/<int:record_id>')
@login_required
@role_required('chief_doctor')
def view_medical_record(record_id):
    """View details of a specific medical record (read-only)"""
    try:
        medical_record = MedicalRecord.query.get_or_404(record_id)
        
        # Decrypt record for viewing
        try:
            decrypted_data = decrypt_medical_record(medical_record.encrypted_blob, medical_record.signature)
        except Exception as e:
            current_app.logger.error(f"Error decrypting record {record_id}: {str(e)}")
            flash('Error decrypting medical record. Record may be corrupted.', 'error')
            decrypted_data = {'error': 'Failed to decrypt record'}
        
        return render_template('chief_doctor/medical_record_detail.html',
                             record=medical_record,
                             decrypted_data=decrypted_data)
    except Exception as e:
        current_app.logger.error(f"View medical record error: {str(e)}")
        flash('Error loading medical record.', 'error')
        return redirect(url_for('chief_doctor.list_medical_records'))

@bp.route('/patient-assignments')
@login_required
@role_required('chief_doctor')
def list_patient_assignments():
    """View and manage patient assignments"""
    try:
        # Get all current assignments
        assignments = db.session.query(PatientAssignment).join(
            Patient, PatientAssignment.patient_id == Patient.id
        ).join(
            User, PatientAssignment.doctor_id == User.id
        ).order_by(Patient.name).all()
        
        # Get unassigned patients
        unassigned_patients = db.session.query(Patient).outerjoin(PatientAssignment).filter(
            PatientAssignment.patient_id.is_(None)
        ).order_by(Patient.name).all()
        
        return render_template('chief_doctor/patient_assignments.html',
                             assignments=assignments,
                             unassigned_patients=unassigned_patients)
    except Exception as e:
        current_app.logger.error(f"List patient assignments error: {str(e)}")
        flash('Error loading patient assignments.', 'error')
        return render_template('chief_doctor/patient_assignments.html',
                             assignments=[],
                             unassigned_patients=[])

@bp.route('/assign-patient', methods=['GET', 'POST'])
@login_required
@role_required('chief_doctor')
def assign_patient():
    """Assign a patient to a curing doctor"""
    form = PatientAssignmentForm()
    if form.validate_on_submit():
        try:
            # Check if patient is already assigned
            existing_assignment = PatientAssignment.query.filter_by(
                patient_id=form.patient_id.data
            ).first()
            
            if existing_assignment:
                flash('Patient is already assigned to a doctor.', 'error')
                return render_template('chief_doctor/patient_assignment_form.html', form=form)
            
            assignment = PatientAssignment(
                patient_id=form.patient_id.data,
                doctor_id=form.doctor_id.data
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            # Log the action
            log_action('ASSIGN_PATIENT', 'PatientAssignment', assignment.id, {
                'patient_id': assignment.patient_id,
                'doctor_id': assignment.doctor_id
            })
            
            flash('Patient assigned successfully.', 'success')
            return redirect(url_for('chief_doctor.list_patient_assignments'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Assign patient error: {str(e)}")
            flash('Error assigning patient. Please try again.', 'error')
    
    return render_template('chief_doctor/patient_assignment_form.html', form=form)

@bp.route('/assignments/<int:assignment_id>/reassign', methods=['GET', 'POST'])
@login_required
@role_required('chief_doctor')
def reassign_patient(assignment_id):
    """Reassign a patient to a different curing doctor"""
    try:
        assignment = PatientAssignment.query.get_or_404(assignment_id)
        form = PatientAssignmentForm()
        
        # Pre-populate form
        form.patient_id.data = assignment.patient_id
        form.patient_id.choices = [(assignment.patient.id, assignment.patient.name)]
        
        if form.validate_on_submit():
            old_doctor_id = assignment.doctor_id
            assignment.doctor_id = form.doctor_id.data
            assignment.assigned_date = datetime.utcnow()
            
            db.session.commit()
            
            # Log the action
            log_action('REASSIGN_PATIENT', 'PatientAssignment', assignment.id, {
                'patient_id': assignment.patient_id,
                'old_doctor_id': old_doctor_id,
                'new_doctor_id': assignment.doctor_id
            })
            
            flash('Patient reassigned successfully.', 'success')
            return redirect(url_for('chief_doctor.list_patient_assignments'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reassign patient error: {str(e)}")
        flash('Error reassigning patient. Please try again.', 'error')
    
    return render_template('chief_doctor/patient_assignment_form.html', 
                         form=form, title='Reassign Patient', assignment=assignment)

@bp.route('/assignments/<int:assignment_id>/remove', methods=['POST'])
@login_required
@role_required('chief_doctor')
def remove_assignment(assignment_id):
    """Remove a patient assignment"""
    try:
        assignment = PatientAssignment.query.get_or_404(assignment_id)
        
        # Log before deletion
        log_action('REMOVE_PATIENT_ASSIGNMENT', 'PatientAssignment', assignment.id, {
            'patient_id': assignment.patient_id,
            'doctor_id': assignment.doctor_id
        })
        
        db.session.delete(assignment)
        db.session.commit()
        
        flash('Patient assignment removed successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Remove assignment error: {str(e)}")
        flash('Error removing assignment. Please try again.', 'error')
    
    return redirect(url_for('chief_doctor.list_patient_assignments'))

@bp.route('/doctors-schedule')
@login_required
@role_required('chief_doctor')
def view_doctors_schedule():
    """View all doctors' appointment schedules"""
    try:
        # Check if show_all parameter is present
        show_all = request.args.get('show_all', '').lower() == 'true'
        
        if show_all:
            # Show all appointments
            appointments = db.session.query(Appointment).join(
                User, Appointment.doctor_id == User.id
            ).filter(
                User.role.in_(['curing_doctor', 'special_doctor'])
            ).order_by(User.username, Appointment.datetime).all()
            
            selected_date = None
        else:
            # Get date filter from query params for date-specific view
            date_str = request.args.get('date')
            if date_str:
                try:
                    filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    filter_date = datetime.now().date()
            else:
                filter_date = datetime.now().date()
            
            # Get appointments for all doctors on the selected date
            next_day = filter_date + timedelta(days=1)
            appointments = db.session.query(Appointment).join(
                User, Appointment.doctor_id == User.id
            ).filter(
                db.and_(
                    Appointment.datetime >= filter_date,
                    Appointment.datetime < next_day,
                    User.role.in_(['curing_doctor', 'special_doctor'])
                )
            ).order_by(User.username, Appointment.datetime).all()
            
            selected_date = filter_date
        
        # Group appointments by doctor
        doctor_schedules = {}
        for appointment in appointments:
            if appointment.doctor.username not in doctor_schedules:
                doctor_schedules[appointment.doctor.username] = []
            doctor_schedules[appointment.doctor.username].append(appointment)
        
        return render_template('chief_doctor/doctors_schedule.html',
                             doctor_schedules=doctor_schedules,
                             selected_date=selected_date)
    except Exception as e:
        current_app.logger.error(f"View doctors schedule error: {str(e)}")
        flash('Error loading doctors schedule.', 'error')
        return render_template('chief_doctor/doctors_schedule.html',
                             doctor_schedules={},
                             selected_date=datetime.now().date())

@bp.route('/reports')
@login_required
@role_required('chief_doctor')
def generate_reports():
    """Generate summary reports"""
    try:
        # Patient count by month (last 12 months)
        from sqlalchemy import extract, func
        from datetime import date
        
        # Calculate date ranges
        current_month = date.today().replace(day=1)
        months = []
        for i in range(12):
            month_date = date(current_month.year - (i // 12), current_month.month - (i % 12), 1)
            if month_date.month <= 0:
                month_date = month_date.replace(year=month_date.year - 1, month=month_date.month + 12)
            months.append(month_date)
        
        # Get patient registrations by month
        patient_stats = []
        for month_date in reversed(months):
            count = Patient.query.filter(
                extract('year', Patient.id) == month_date.year,
                extract('month', Patient.id) == month_date.month
            ).count()
            patient_stats.append({
                'month': month_date.strftime('%Y-%m'),
                'count': count
            })
        
        # Appointment statistics
        total_appointments = Appointment.query.count()
        completed_appointments = Appointment.query.filter_by(status='completed').count()
        cancelled_appointments = Appointment.query.filter_by(status='cancelled').count()
        
        # Upcoming appointments (next 30 days)
        today = datetime.now().date()
        next_month = today + timedelta(days=30)
        upcoming_appointments = Appointment.query.filter(
            db.and_(
                Appointment.datetime >= today,
                Appointment.datetime < next_month,
                Appointment.status == 'scheduled'
            )
        ).count()
        
        # Medical records by type
        record_type_stats = db.session.query(
            MedicalRecord.record_type,
            func.count(MedicalRecord.id).label('count')
        ).group_by(MedicalRecord.record_type).all()
        
        return render_template('chief_doctor/reports.html',
                             patient_stats=patient_stats,
                             total_appointments=total_appointments,
                             completed_appointments=completed_appointments,
                             cancelled_appointments=cancelled_appointments,
                             upcoming_appointments=upcoming_appointments,
                             record_type_stats=dict(record_type_stats))
    except Exception as e:
        current_app.logger.error(f"Generate reports error: {str(e)}")
        flash('Error generating reports.', 'error')
        return render_template('chief_doctor/reports.html')

# TODO: Students can extend this section with additional chief doctor functionality:
# - Advanced reporting and analytics
# - Resource allocation optimization
# - Quality metrics tracking
# - Department management
# - Performance dashboards 