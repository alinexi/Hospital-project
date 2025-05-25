#!/usr/bin/env python3
"""Database initialization script for the Hospital Management System."""

from app import create_app
from app.models import db, User, Patient
from werkzeug.security import generate_password_hash
from datetime import datetime, date

def init_database():
    """Initialize the database and create default users."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if users already exist
        if User.query.first():
            print("Users already exist in database.")
            # Check if patients exist, if not create sample patients
            if not Patient.query.first():
                create_sample_patients()
            return
        
        # Create default users for each role
        default_users = [
            {
                'username': 'admin',
                'email': 'admin@hospital.com',
                'password': 'admin123',
                'role': 'sysadmin'
            },
            {
                'username': 'receptionist1',
                'email': 'receptionist@hospital.com',
                'password': 'recept123',
                'role': 'receptionist'
            },
            {
                'username': 'chief1',
                'email': 'chief@hospital.com',
                'password': 'chief123',
                'role': 'chief_doctor'
            },
            {
                'username': 'doctor1',
                'email': 'doctor@hospital.com',
                'password': 'doctor123',
                'role': 'curing_doctor'
            },
            {
                'username': 'specialist1',
                'email': 'specialist@hospital.com',
                'password': 'special123',
                'role': 'special_doctor'
            },
            {
                'username': 'patient1',
                'email': 'patient@hospital.com',
                'password': 'patient123',
                'role': 'patient'
            }
        ]
        
        # Create users
        for user_data in default_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role']
            )
            db.session.add(user)
        
        db.session.commit()
        print("Default users created successfully!")
        
        # Create sample patients
        create_sample_patients()
        
        print("\nDefault login credentials:")
        for user_data in default_users:
            print(f"  {user_data['role']}: {user_data['username']} / {user_data['password']}")

def create_sample_patients():
    """Create sample patients for testing"""
    sample_patients = [
        {
            'name': 'John Doe',
            'date_of_birth': date(1985, 3, 15),
            'demographics': 'Address: 123 Main St, City, State 12345\nPhone: (555) 123-4567\nEmergency Contact: Jane Doe (555) 987-6543',
            'username': 'patient1'
        },
        {
            'name': 'Mary Smith',
            'date_of_birth': date(1990, 7, 22),
            'demographics': 'Address: 456 Oak Ave, City, State 12346\nPhone: (555) 234-5678\nEmergency Contact: Bob Smith (555) 876-5432',
            'username': None  # Patient without user account
        },
        {
            'name': 'Robert Johnson',
            'date_of_birth': date(1978, 11, 8),
            'demographics': 'Address: 789 Pine Rd, City, State 12347\nPhone: (555) 345-6789\nEmergency Contact: Lisa Johnson (555) 765-4321',
            'username': None
        },
        {
            'name': 'Emily Davis',
            'date_of_birth': date(1995, 5, 14),
            'demographics': 'Address: 321 Elm St, City, State 12348\nPhone: (555) 456-7890\nEmergency Contact: Michael Davis (555) 654-3210',
            'username': None
        },
        {
            'name': 'William Brown',
            'date_of_birth': date(1982, 9, 3),
            'demographics': 'Address: 654 Maple Dr, City, State 12349\nPhone: (555) 567-8901\nEmergency Contact: Sarah Brown (555) 543-2109',
            'username': None
        }
    ]
    
    for patient_data in sample_patients:
        # Find user if username is provided
        user_id = None
        if patient_data['username']:
            user = User.query.filter_by(username=patient_data['username']).first()
            if user:
                user_id = user.id
        
        patient = Patient(
            name=patient_data['name'],
            date_of_birth=patient_data['date_of_birth'],
            demographics=patient_data['demographics'],
            user_id=user_id
        )
        db.session.add(patient)
    
    db.session.commit()
    print("Sample patients created successfully!")

if __name__ == '__main__':
    init_database() 