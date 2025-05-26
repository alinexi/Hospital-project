from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from hospital.models import db, Patient, Doctor, AccessGrant, AccessLog
from datetime import datetime

special_doctor = Blueprint('special_doctor', __name__)

@special_doctor.route('/special-doctor/dashboard')
@login_required
def dashboard():
    # ... existing code ...

@special_doctor.route('/special-doctor/access-grants')
@login_required
def access_grants():
    # ... existing code ...

@special_doctor.route('/special-doctor/access-logs')
@login_required
def access_logs():
    # ... existing code ...

@special_doctor.route('/special-doctor/revoke-access/<int:grant_id>', methods=['POST'])
@login_required
def revoke_access(grant_id):
    # ... existing code ... 