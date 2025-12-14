from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User
from ..database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 1. If user is ALREADY logged in
    if current_user.is_authenticated:
        # FIX A: Check 'current_user' (not 'user')
        if not current_user.is_active:
            # FIX B: If deactivated, force logout immediately. Do NOT send to dashboard.
            logout_user()
            flash('This account has been deactivated. Contact the Captain.', 'danger')
            return redirect(url_for('auth.login'))
            
        # If active, redirect to correct dashboard
        if current_user.role in ['admin', 'super_admin']:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('associate.dashboard'))

    # 2. Handle Login Form Submission
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # FIX C: Check status BEFORE logging them in
            if not user.is_active:
                flash('This account has been deactivated. Contact the Captain.', 'danger')
                return redirect(url_for('auth.login'))

            # Only login if active
            login_user(user)
            flash('Logged in successfully!', 'success')
            
            if user.role in ['admin', 'super_admin']:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('associate.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))