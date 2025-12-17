from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, SystemLog  
from ..database import db
import string
import secrets
from flask_mail import Message
from .. import mail  # <--- Import the mail instance we created in __init__.py

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


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_settings():
    if request.method == 'POST':
        # --- GET BASIC INFO ---
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        address = request.form.get('address')
        file = request.files.get('profile_pic')

        # --- GET PASSWORD FIELDS ---
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        changes = [] # Track changes for logging

        # 1. HANDLE PASSWORD CHANGE (Priority Check)
        if new_password:
            if not current_password:
                flash('Please enter your current password to set a new one.', 'warning')
                return render_template('auth/profile.html')
            
            if not current_user.check_password(current_password):
                flash('Incorrect current password.', 'danger')
                return render_template('auth/profile.html')
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return render_template('auth/profile.html')

            # Apply Change
            current_user.set_password(new_password)
            changes.append("Password")

        # 2. CHECK DUPLICATES (Username/Email)
        if username != current_user.username:
            if User.query.filter_by(username=username).first():
                flash('Username already taken.', 'danger')
                return render_template('auth/profile.html')
            changes.append("Username")
        
        if email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
                return render_template('auth/profile.html')
            changes.append("Email")

        if name != current_user.name:
            changes.append("Name")
        if address != current_user.address:
            changes.append("Address")

        # 3. HANDLE PICTURE UPLOAD
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in {'png', 'jpg', 'jpeg', 'gif'}:
                timestamp = int(time.time())
                new_filename = f"user_{current_user.user_id}_{timestamp}.{ext}"
                upload_folder = os.path.join(current_app.root_path, 'static', 'profile_pics')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Delete old pic
                if current_user.pic_path and current_user.pic_path != 'default.png':
                    old_path = os.path.join(upload_folder, current_user.pic_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                file.save(os.path.join(upload_folder, new_filename))
                current_user.pic_path = new_filename
                changes.append("Profile Picture")

        # 4. SAVE CHANGES TO DB
        current_user.username = username
        current_user.email = email
        current_user.name = name
        current_user.address = address
        
        # 5. LOG THE UPDATE
        if changes:
            log_details = f"Updated: {', '.join(changes)}"
            log = SystemLog(
                actor_id=current_user.user_id,
                action_type='Update User', 
                target_change=f'Profile: {current_user.name}',
                details=log_details
            )
            db.session.add(log)
            db.session.commit()
            flash('Profile and security settings updated successfully!', 'success')
        else:
            flash('No changes were made.', 'info')

        return redirect(url_for('auth.profile_settings'))

    return render_template('auth/profile.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        # 1. Verify User
        user = User.query.filter_by(username=username, email=email).first()

        if user:
            # 2. Generate New Random Password
            alphabet = string.ascii_letters + string.digits
            new_password = ''.join(secrets.choice(alphabet) for i in range(8))
            
            # 3. Update Database
            user.set_password(new_password)
            
            # Log the Reset
            log = SystemLog(
                actor_id=user.user_id,
                action_type='Password Reset',
                target_change=f'User: {user.username}',
                details="Password reset via 'Forgot Password'"
            )
            db.session.add(log)
            db.session.commit()

            # 4. Send Email
            try:
                msg = Message("Your New Password", recipients=[user.email])
                msg.body = f"Hello {user.name},\n\nYour password has been successfully reset.\n\nNew Password: {new_password}\n\nPlease log in and change this immediately in your Profile Settings."
                mail.send(msg)
                flash(f'A new password has been sent to {email}.', 'success')
            
            except Exception as e:
                # Fallback for Development (If SMTP is not configured)
                print(f"EMAIL ERROR: {e}")
                print(f"DEV MODE - NEW PASSWORD FOR {username}: {new_password}")
                flash('Email system not configured. check SERVER CONSOLE for the new password.', 'warning')

            return redirect(url_for('auth.login'))
        
        else:
            flash('No account found with that username and email combination.', 'danger')

    return render_template('auth/forgot_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Log the Logout
    log = SystemLog(
        actor_id=current_user.user_id,
        action_type='Logout',
        target_change=f'User: {current_user.username}',
        details="User logged out"
    )
    db.session.add(log)
    db.session.commit()

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))