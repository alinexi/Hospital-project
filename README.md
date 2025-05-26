# Hospital Management System

## What is this project?
This is a Hospital Management System that helps hospitals manage their daily operations. It's like a digital assistant that helps keep track of patients, doctors, appointments, and medical records in a secure way.

## How to Get Started

### Prerequisites
- Python 3.x installed on your computer
- Basic understanding of using a web browser

### Installation Steps
1. Download or clone this project to your computer
2. Open a terminal/command prompt in the project folder
3. Create a virtual environment (this keeps the project separate from other Python projects):
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On Mac/Linux: `source venv/bin/activate`
5. Install required packages:
   ```
   pip install -r requirements.txt
   ```
6. Run the application:
   ```
   python run.py
   ```
7. Open your web browser and go to: `http://127.0.0.1:5000`

## Main Features

### 1. User Management
- Different types of users: Patients, Doctors, and Administrators
- Secure login system
- Password protection for all accounts

### 2. Patient Management
- Register new patients
- View patient history
- Schedule appointments
- Access medical records

### 3. Doctor Features
- View assigned patients
- Manage appointments
- Update patient records
- Write prescriptions

### 4. Appointment System
- Schedule appointments
- View upcoming appointments
- Cancel or reschedule appointments
- Receive appointment reminders

### 5. Medical Records
- Secure storage of patient information
- Easy access to medical history
- Prescription management
- Test results tracking

## Security Features
- All data is encrypted for protection
- Secure login system
- Protected access to sensitive information
- Regular security updates

## Need Help?
If you encounter any issues or have questions:
1. Check the error messages carefully
2. Make sure all installation steps were completed
3. Verify that you're using the correct Python version
4. Ensure all required packages are installed

## Technical Details (For Developers)
This project is built using:
- Flask (Python web framework)
- SQLAlchemy (Database management)
- Flask-Login (User authentication)
- PyCryptodome (Security features)
- ReportLab (PDF generation)

## Important Notes
- Always keep your login credentials secure
- Regularly backup your data
- Keep the system updated
- Report any security concerns immediately

## Support
For technical support or questions, please contact the system administrator or create an issue in the project repository. 