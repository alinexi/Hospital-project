#!/usr/bin/env python3
"""Database initialization script for the Hospital Management System."""

from app import create_app
from app.models import db, User
from werkzeug.security import generate_password_hash

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
        print("\nDefault login credentials:")
        for user_data in default_users:
            print(f"  {user_data['role']}: {user_data['username']} / {user_data['password']}")

if __name__ == '__main__':
    init_database() 