#!/usr/bin/env python3
"""
Script to add comprehensive sample data to the Hospital Management System database.
This script adds:
- Multiple users with different roles
- Patient medical records (encrypted and signed)
- Access grants for doctors to view specific patient records
- Patient assignments to doctors
- Appointments
"""

from app import create_app
from app.models import db, User, Patient, MedicalRecord, AccessGrant, PatientAssignment, Appointment, AuditLog
from app.utils.encryption import encrypt_medical_record, generate_rsa_keys
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

def add_sample_data():
    """Add comprehensive sample data to the database"""
    app = create_app()
    
    with app.app_context():
        # Generate RSA keys if they don't exist
        generate_rsa_keys()
        
        print("Adding sample data to Hospital Management System...")
        
        # Add multiple users with different roles
        add_users()
        
        # Add more patients
        add_patients()
        
        # Add patient assignments
        add_patient_assignments()
        
        # Add medical records
        add_medical_records()
        
        # Add access grants
        add_access_grants()
        
        # Add appointments
        add_appointments()
        
        # Add audit logs
        add_audit_logs()
        
        print("\nSample data added successfully!")
        print_summary()

def add_users():
    """Add multiple users with different roles"""
    print("Adding users...")
    
    users_data = [
        # System Administrators
        {'username': 'admin_john', 'email': 'john.admin@hospital.com', 'password': 'admin123', 'role': 'sysadmin'},
        {'username': 'admin_sarah', 'email': 'sarah.admin@hospital.com', 'password': 'admin456', 'role': 'sysadmin'},
        
        # Receptionists
        {'username': 'receptionist_mary', 'email': 'mary.reception@hospital.com', 'password': 'recept123', 'role': 'receptionist'},
        {'username': 'receptionist_lisa', 'email': 'lisa.reception@hospital.com', 'password': 'recept456', 'role': 'receptionist'},
        {'username': 'receptionist_anna', 'email': 'anna.reception@hospital.com', 'password': 'recept789', 'role': 'receptionist'},
        
        # Chief Doctors
        {'username': 'chief_wilson', 'email': 'dr.wilson@hospital.com', 'password': 'chief123', 'role': 'chief_doctor'},
        {'username': 'chief_anderson', 'email': 'dr.anderson@hospital.com', 'password': 'chief456', 'role': 'chief_doctor'},
        
        # Curing Doctors (Primary Care)
        {'username': 'dr_smith', 'email': 'dr.smith@hospital.com', 'password': 'doctor123', 'role': 'curing_doctor'},
        {'username': 'dr_johnson', 'email': 'dr.johnson@hospital.com', 'password': 'doctor456', 'role': 'curing_doctor'},
        {'username': 'dr_brown', 'email': 'dr.brown@hospital.com', 'password': 'doctor789', 'role': 'curing_doctor'},
        {'username': 'dr_davis', 'email': 'dr.davis@hospital.com', 'password': 'doctor101', 'role': 'curing_doctor'},
        {'username': 'dr_miller', 'email': 'dr.miller@hospital.com', 'password': 'doctor202', 'role': 'curing_doctor'},
        
        # Special Doctors (Specialists)
        {'username': 'specialist_garcia', 'email': 'dr.garcia@hospital.com', 'password': 'special123', 'role': 'special_doctor'},
        {'username': 'specialist_martinez', 'email': 'dr.martinez@hospital.com', 'password': 'special456', 'role': 'special_doctor'},
        {'username': 'specialist_rodriguez', 'email': 'dr.rodriguez@hospital.com', 'password': 'special789', 'role': 'special_doctor'},
        {'username': 'specialist_hernandez', 'email': 'dr.hernandez@hospital.com', 'password': 'special101', 'role': 'special_doctor'},
        {'username': 'specialist_lopez', 'email': 'dr.lopez@hospital.com', 'password': 'special202', 'role': 'special_doctor'},
        
        # Patients with user accounts
        {'username': 'patient_alice', 'email': 'alice.patient@email.com', 'password': 'patient123', 'role': 'patient'},
        {'username': 'patient_bob', 'email': 'bob.patient@email.com', 'password': 'patient456', 'role': 'patient'},
        {'username': 'patient_carol', 'email': 'carol.patient@email.com', 'password': 'patient789', 'role': 'patient'},
        {'username': 'patient_david', 'email': 'david.patient@email.com', 'password': 'patient101', 'role': 'patient'},
        {'username': 'patient_eve', 'email': 'eve.patient@email.com', 'password': 'patient202', 'role': 'patient'},
    ]
    
    for user_data in users_data:
        # Check if user already exists
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if not existing_user:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role']
            )
            db.session.add(user)
    
    db.session.commit()
    print(f"Users added: {len(users_data)} users")

def add_patients():
    """Add multiple patients"""
    print("Adding patients...")
    
    patients_data = [
        # Patients with user accounts
        {'name': 'Alice Thompson', 'dob': date(1985, 3, 15), 'demographics': 'Address: 123 Maple St, Springfield, IL 62701\nPhone: (217) 555-1234\nEmergency Contact: John Thompson (217) 555-5678\nInsurance: Blue Cross Blue Shield\nAllergies: Penicillin', 'username': 'patient_alice'},
        {'name': 'Bob Wilson', 'dob': date(1978, 7, 22), 'demographics': 'Address: 456 Oak Ave, Springfield, IL 62702\nPhone: (217) 555-2345\nEmergency Contact: Mary Wilson (217) 555-6789\nInsurance: Aetna\nAllergies: None known', 'username': 'patient_bob'},
        {'name': 'Carol Martinez', 'dob': date(1992, 11, 8), 'demographics': 'Address: 789 Pine Rd, Springfield, IL 62703\nPhone: (217) 555-3456\nEmergency Contact: Luis Martinez (217) 555-7890\nInsurance: United Healthcare\nAllergies: Shellfish, Latex', 'username': 'patient_carol'},
        {'name': 'David Chen', 'dob': date(1965, 5, 14), 'demographics': 'Address: 321 Elm St, Springfield, IL 62704\nPhone: (217) 555-4567\nEmergency Contact: Linda Chen (217) 555-8901\nInsurance: Medicare\nAllergies: Aspirin', 'username': 'patient_david'},
        {'name': 'Eve Rodriguez', 'dob': date(1988, 9, 3), 'demographics': 'Address: 654 Cedar Dr, Springfield, IL 62705\nPhone: (217) 555-5678\nEmergency Contact: Maria Rodriguez (217) 555-9012\nInsurance: Medicaid\nAllergies: Iodine', 'username': 'patient_eve'},
        
        # Patients without user accounts
        {'name': 'Frank Anderson', 'dob': date(1972, 12, 18), 'demographics': 'Address: 987 Birch Ln, Springfield, IL 62706\nPhone: (217) 555-6789\nEmergency Contact: Susan Anderson (217) 555-0123\nInsurance: Cigna\nAllergies: Sulfa drugs', 'username': None},
        {'name': 'Grace Taylor', 'dob': date(1995, 4, 27), 'demographics': 'Address: 147 Willow Way, Springfield, IL 62707\nPhone: (217) 555-7890\nEmergency Contact: Robert Taylor (217) 555-1234\nInsurance: Blue Cross Blue Shield\nAllergies: Peanuts', 'username': None},
        {'name': 'Henry Jackson', 'dob': date(1980, 8, 12), 'demographics': 'Address: 258 Spruce Ave, Springfield, IL 62708\nPhone: (217) 555-8901\nEmergency Contact: Jennifer Jackson (217) 555-2345\nInsurance: Kaiser Permanente\nAllergies: None known', 'username': None},
        {'name': 'Iris White', 'dob': date(1963, 1, 30), 'demographics': 'Address: 369 Ash Blvd, Springfield, IL 62709\nPhone: (217) 555-9012\nEmergency Contact: Michael White (217) 555-3456\nInsurance: Medicare\nAllergies: Morphine', 'username': None},
        {'name': 'Jack Harris', 'dob': date(1990, 6, 9), 'demographics': 'Address: 741 Poplar St, Springfield, IL 62710\nPhone: (217) 555-0123\nEmergency Contact: Sarah Harris (217) 555-4567\nInsurance: Humana\nAllergies: Codeine', 'username': None},
        {'name': 'Kelly Moore', 'dob': date(1987, 10, 25), 'demographics': 'Address: 852 Hickory Rd, Springfield, IL 62711\nPhone: (217) 555-1235\nEmergency Contact: Daniel Moore (217) 555-5679\nInsurance: Anthem\nAllergies: Latex, Nickel', 'username': None},
        {'name': 'Liam Clark', 'dob': date(1975, 3, 7), 'demographics': 'Address: 963 Sycamore Dr, Springfield, IL 62712\nPhone: (217) 555-2346\nEmergency Contact: Emma Clark (217) 555-6780\nInsurance: UnitedHealth\nAllergies: None known', 'username': None},
    ]
    
    for patient_data in patients_data:
        # Check if patient already exists
        existing_patient = Patient.query.filter_by(name=patient_data['name']).first()
        if not existing_patient:
            # Find user if username is provided
            user_id = None
            if patient_data['username']:
                user = User.query.filter_by(username=patient_data['username']).first()
                if user:
                    user_id = user.id
            
            patient = Patient(
                name=patient_data['name'],
                date_of_birth=patient_data['dob'],
                demographics=patient_data['demographics'],
                user_id=user_id
            )
            db.session.add(patient)
    
    db.session.commit()
    print(f"Patients added: {len(patients_data)} patients")

def add_patient_assignments():
    """Assign patients to curing doctors"""
    print("Adding patient assignments...")
    
    # Get all patients and curing doctors
    patients = Patient.query.all()
    curing_doctors = User.query.filter_by(role='curing_doctor').all()
    
    assignments_count = 0
    for patient in patients:
        # Check if patient already has an assignment
        existing_assignment = PatientAssignment.query.filter_by(patient_id=patient.id).first()
        if not existing_assignment and curing_doctors:
            # Randomly assign to a curing doctor
            doctor = random.choice(curing_doctors)
            assignment = PatientAssignment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                assigned_date=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            db.session.add(assignment)
            assignments_count += 1
    
    db.session.commit()
    print(f"Patient assignments added: {assignments_count} assignments")

def add_medical_records():
    """Add encrypted medical records for patients"""
    print("Adding medical records...")
    
    patients = Patient.query.all()
    doctors = User.query.filter(User.role.in_(['curing_doctor', 'chief_doctor', 'special_doctor'])).all()
    
    record_templates = [
        {
            'type': 'diagnosis',
            'content': 'Patient presents with symptoms of hypertension. Blood pressure reading: 140/90 mmHg. Recommended lifestyle changes and prescribed Lisinopril 10mg daily.',
            'diagnosis': 'Essential Hypertension',
            'medications': ['Lisinopril 10mg daily'],
            'vital_signs': {'bp': '140/90', 'pulse': '72', 'temp': '98.6°F', 'resp': '16'}
        },
        {
            'type': 'follow_up',
            'content': 'Follow-up visit for diabetes management. HbA1c: 7.2%. Blood glucose levels improving with current medication regimen.',
            'diagnosis': 'Type 2 Diabetes Mellitus',
            'medications': ['Metformin 500mg twice daily', 'Glipizide 5mg daily'],
            'vital_signs': {'bp': '135/85', 'pulse': '76', 'temp': '98.4°F', 'resp': '18'}
        },
        {
            'type': 'treatment',
            'content': 'Patient underwent minor surgical procedure for lipoma removal. Procedure completed successfully without complications.',
            'diagnosis': 'Lipoma, subcutaneous',
            'medications': ['Ibuprofen 400mg as needed for pain'],
            'vital_signs': {'bp': '125/80', 'pulse': '68', 'temp': '98.2°F', 'resp': '16'}
        },
        {
            'type': 'consultation',
            'content': 'Cardiology consultation for chest pain evaluation. EKG normal. Stress test recommended.',
            'diagnosis': 'Chest pain, unspecified',
            'medications': ['Aspirin 81mg daily'],
            'vital_signs': {'bp': '130/85', 'pulse': '78', 'temp': '98.7°F', 'resp': '17'}
        },
        {
            'type': 'emergency',
            'content': 'Emergency department visit for acute allergic reaction. Treated with epinephrine and antihistamines. Full recovery.',
            'diagnosis': 'Allergic reaction to food',
            'medications': ['EpiPen prescribed', 'Benadryl 25mg as needed'],
            'vital_signs': {'bp': '110/70', 'pulse': '92', 'temp': '99.1°F', 'resp': '20'}
        }
    ]
    
    records_count = 0
    for patient in patients:
        # Add 2-4 random medical records per patient
        num_records = random.randint(2, 4)
        for _ in range(num_records):
            template = random.choice(record_templates)
            author = random.choice(doctors)
            
            # Create medical record data
            record_data = {
                'patient_name': patient.name,
                'patient_id': patient.id,
                'record_type': template['type'],
                'content': template['content'],
                'diagnosis': template['diagnosis'],
                'medications': template['medications'],
                'vital_signs': template['vital_signs'],
                'author': author.username,
                'date': (datetime.utcnow() - timedelta(days=random.randint(1, 180))).isoformat(),
                'notes': f"Record created by {author.username} for patient {patient.name}"
            }
            
            # Encrypt and sign the medical record
            encrypted_blob, signature = encrypt_medical_record(record_data)
            
            medical_record = MedicalRecord(
                patient_id=patient.id,
                author_id=author.id,
                encrypted_blob=encrypted_blob,
                signature=signature,
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 180)),
                record_type=template['type']
            )
            db.session.add(medical_record)
            records_count += 1
    
    db.session.commit()
    print(f"Medical records added: {records_count} encrypted records")

def add_access_grants():
    """Add access grants for special doctors to view specific medical records"""
    print("Adding access grants...")
    
    medical_records = MedicalRecord.query.all()
    special_doctors = User.query.filter_by(role='special_doctor').all()
    chief_doctors = User.query.filter_by(role='chief_doctor').all()
    granting_doctors = chief_doctors  # Only chief doctors can grant access
    
    grants_count = 0
    for record in medical_records:
        # Randomly grant access to 1-2 special doctors per record
        if special_doctors and granting_doctors:
            num_grants = random.randint(0, 2)  # Some records may have no special access
            granted_doctors = random.sample(special_doctors, min(num_grants, len(special_doctors)))
            granting_doctor = random.choice(granting_doctors)
            
            for doctor in granted_doctors:
                # Check if access grant already exists
                existing_grant = AccessGrant.query.filter_by(
                    record_id=record.id,
                    granted_to_user_id=doctor.id
                ).first()
                
                if not existing_grant:
                    access_grant = AccessGrant(
                        record_id=record.id,
                        granted_to_user_id=doctor.id,
                        granted_by_user_id=granting_doctor.id,
                        granted_date=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    )
                    db.session.add(access_grant)
                    grants_count += 1
    
    db.session.commit()
    print(f"Access grants added: {grants_count} grants")

def add_appointments():
    """Add appointments between patients and doctors"""
    print("Adding appointments...")
    
    patients = Patient.query.all()
    doctors = User.query.filter(User.role.in_(['curing_doctor', 'special_doctor'])).all()
    
    appointments_count = 0
    for patient in patients:
        # Add 1-3 appointments per patient (past, present, future)
        num_appointments = random.randint(1, 3)
        for _ in range(num_appointments):
            doctor = random.choice(doctors)
            
            # Create appointments in the past, present, and future
            appointment_date = datetime.utcnow() + timedelta(
                days=random.randint(-60, 30),  # 60 days ago to 30 days in future
                hours=random.randint(8, 17),   # Business hours
                minutes=random.choice([0, 15, 30, 45])  # Quarter-hour intervals
            )
            
            status_options = ['scheduled', 'completed', 'cancelled', 'rescheduled']
            # Past appointments are more likely to be completed
            if appointment_date < datetime.utcnow():
                status = random.choice(['completed', 'cancelled', 'completed', 'completed'])
            else:
                status = 'scheduled'
            
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                datetime=appointment_date,
                status=status,
                notes=f"Appointment with {doctor.username} for {patient.name}"
            )
            db.session.add(appointment)
            appointments_count += 1
    
    db.session.commit()
    print(f"Appointments added: {appointments_count} appointments")

def add_audit_logs():
    """Add sample audit logs for tracking system activity"""
    print("Adding audit logs...")
    
    users = User.query.all()
    patients = Patient.query.all()
    
    audit_actions = [
        'LOGIN',
        'LOGOUT',
        'VIEW_PATIENT_RECORD',
        'CREATE_MEDICAL_RECORD',
        'GRANT_ACCESS',
        'REVOKE_ACCESS',
        'UPDATE_PATIENT_INFO',
        'CREATE_APPOINTMENT',
        'CANCEL_APPOINTMENT'
    ]
    
    logs_count = 0
    for user in users:
        # Add 5-15 audit logs per user
        num_logs = random.randint(5, 15)
        for _ in range(num_logs):
            action = random.choice(audit_actions)
            target_patient = random.choice(patients) if patients else None
            
            audit_log = AuditLog(
                user_id=user.id,
                action=action,
                target_id=target_patient.id if target_patient else None,
                target_type='Patient' if target_patient else 'System',
                details=f"User {user.username} performed {action}",
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            db.session.add(audit_log)
            logs_count += 1
    
    db.session.commit()
    print(f"Audit logs added: {logs_count} logs")

def print_summary():
    """Print a summary of all data in the database"""
    print("\n" + "="*50)
    print("DATABASE SUMMARY")
    print("="*50)
    
    # Users by role
    roles = ['sysadmin', 'receptionist', 'chief_doctor', 'curing_doctor', 'special_doctor', 'patient']
    for role in roles:
        count = User.query.filter_by(role=role).count()
        print(f"{role.replace('_', ' ').title()}: {count} users")
    
    print(f"\nTotal Users: {User.query.count()}")
    print(f"Total Patients: {Patient.query.count()}")
    print(f"Total Medical Records: {MedicalRecord.query.count()}")
    print(f"Total Access Grants: {AccessGrant.query.count()}")
    print(f"Total Patient Assignments: {PatientAssignment.query.count()}")
    print(f"Total Appointments: {Appointment.query.count()}")
    print(f"Total Audit Logs: {AuditLog.query.count()}")
    
    print("\n" + "="*50)
    print("SAMPLE LOGIN CREDENTIALS")
    print("="*50)
    
    # Show sample credentials for each role
    sample_users = [
        User.query.filter_by(role='sysadmin').first(),
        User.query.filter_by(role='receptionist').first(),
        User.query.filter_by(role='chief_doctor').first(),
        User.query.filter_by(role='curing_doctor').first(),
        User.query.filter_by(role='special_doctor').first(),
        User.query.filter_by(role='patient').first()
    ]
    
    for user in sample_users:
        if user:
            # Extract password from username pattern (demo purposes only)
            if 'admin' in user.username:
                password = 'admin123' if 'john' in user.username else 'admin456'
            elif 'receptionist' in user.username:
                password = 'recept123' if 'mary' in user.username else 'recept456'
            elif 'chief' in user.username:
                password = 'chief123' if 'wilson' in user.username else 'chief456'
            elif 'dr_' in user.username:
                password = 'doctor123' if 'smith' in user.username else 'doctor456'
            elif 'specialist' in user.username:
                password = 'special123' if 'garcia' in user.username else 'special456'
            elif 'patient' in user.username:
                password = 'patient123' if 'alice' in user.username else 'patient456'
            else:
                password = '***'
            
            print(f"{user.role.replace('_', ' ').title()}: {user.username} / {password}")

if __name__ == '__main__':
    add_sample_data() 