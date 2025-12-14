from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, stream_with_context
from flask_login import login_required, current_user
from datetime import datetime
from ..utils.decorators import admin_required
from ..models import Project, Request, User, SystemLog, AdminVote
from ..database import db
from sqlalchemy import func
import csv
from io import StringIO
import os
import re 
from werkzeug.utils import secure_filename
from flask import current_app

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Allow both Officers (admin) and Captain (super_admin)
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('main.index'))

    # 1. Analytics
    total_projects = Project.query.count()
    approved_projects = Project.query.filter(Project.current_status != 'Cancelled').count()
    pending_requests = Request.query.filter_by(status='Pending').count()
    total_funds = db.session.query(db.func.sum(Project.given_fund)).scalar() or 0.0

    # 2. Recent Projects
    projects = Project.query.join(Request).order_by(Project.approval_date.desc()).limit(5).all()

    return render_template('admin/dashboard.html', 
                           total_projects=total_projects,
                           approved_projects=approved_projects,
                           pending_requests=pending_requests,
                           total_funds=total_funds,
                           projects=projects)

@admin_bp.route('/requests')
@login_required
def requests_list():
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('main.index'))

    # Fetch Pending Requests
    requests = Request.query.filter_by(status='Pending').all()
    
    # Calculate Vote Counts for each request (For the Captain to see)
    for req in requests:
        req.approve_count = AdminVote.query.filter_by(request_id=req.request_id, vote='Approve').count()
        req.reject_count = AdminVote.query.filter_by(request_id=req.request_id, vote='Reject').count()
        # Check if CURRENT user has already voted
        req.user_voted = AdminVote.query.filter_by(request_id=req.request_id, admin_id=current_user.user_id).first()

    return render_template('admin/requests_list.html', requests=requests)

# Helper function to check allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/register-official', methods=['GET', 'POST'])
@login_required
def register_official():
    if current_user.role != 'super_admin':
        flash('Only the Captain can register new officials.', 'danger')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        # 1. Get Data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role')
        occupation = request.form.get('occupation')
        address = request.form.get('address')
        relation = request.form.get('relation')
        file = request.files.get('profile_pic')

        # --- VALIDATION LOGIC ---
        error_field = None # Track which field failed

        # A. Required Fields Check
        required_fields = {
            "name": name,
            "username": username,
            "email": email,
            "password": password,
            "occupation": occupation,
            "address": address
        }
        
        for field_key, value in required_fields.items():
            if not value or not value.strip():
                flash(f'{field_key.capitalize()} is required.', 'danger')
                # Return template immediately to save data
                return render_template('admin/register_associate.html', error_field=field_key)

        # B. Email Format
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email format.', 'danger')
            return render_template('admin/register_associate.html', error_field='email')

        # C. Duplicate Check
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                flash('Username is already taken.', 'danger')
                return render_template('admin/register_associate.html', error_field='username')
            else:
                flash('Email is already registered.', 'danger')
                return render_template('admin/register_associate.html', error_field='email')

        # --- SAVE USER (Only runs if validations pass) ---
        pic_filename = 'default.png'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            import time
            unique_filename = f"{int(time.time())}_{filename}"
            file_path = os.path.join(current_app.root_path, 'static', 'profile_pics', unique_filename)
            file.save(file_path)
            pic_filename = unique_filename

        new_user = User(
            username=username, email=email, role=role, name=name, 
            occupation=occupation, relation_to_admin=relation, 
            address=address, pic_path=pic_filename
        )
        new_user.set_password(password)
        db.session.add(new_user)
        
        # Log it
        log = SystemLog(
            actor_id=current_user.user_id,
            action_type='Create User',
            target_change=f'Official: {name}',
            details=f"Registered {occupation}: {name}. Address: {address}"
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Successfully registered {name}!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/register_associate.html')

@admin_bp.route('/requests/<int:request_id>/vote', methods=['POST'])
@login_required
def cast_vote(request_id):
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('main.index'))

    req = Request.query.get_or_404(request_id)
    vote_choice = request.form.get('vote') # 'Approve' or 'Reject'
    remarks = request.form.get('remarks')
    
    # 1. Check if user already voted
    existing_vote = AdminVote.query.filter_by(request_id=req.request_id, admin_id=current_user.user_id).first()
    if existing_vote:
        flash('You have already voted on this request.', 'warning')
        return redirect(url_for('admin.requests_list'))

    # 2. Record Vote
    new_vote = AdminVote(
        request_id=req.request_id,
        admin_id=current_user.user_id,
        vote=vote_choice,
        remarks=remarks
    )
    db.session.add(new_vote)
    db.session.commit()
    
    flash('Vote cast successfully!', 'success')
    return redirect(url_for('admin.requests_list'))

@admin_bp.route('/requests/<int:request_id>/finalize', methods=['POST'])
@login_required
def finalize_approval(request_id):
    # ONLY SUPER ADMIN (Captain) can do this
    if current_user.role != 'super_admin':
        flash('Only the Captain can finalize approvals.', 'danger')
        return redirect(url_for('admin.requests_list'))

    req = Request.query.get_or_404(request_id)
    action = request.form.get('action') # 'Approve' or 'Reject'

    if action == 'Approve':
        req.status = 'Approved'
        # Create Project
        proj = Project(
            request_id=req.request_id,
            current_status='Ongoing',
            given_fund=req.fund_amount,
            approval_date=datetime.utcnow()
        )
        db.session.add(proj)
        details = f"Captain Finalized Approval (Funds: {req.fund_amount})"
        flash('Request officially APPROVED. Project created.', 'success')

    else:
        req.status = 'Rejected'
        details = "Captain Finalized Rejection"
        flash('Request officially REJECTED.', 'warning')

    # Log it
    log = SystemLog(
        actor_id=current_user.user_id,
        action_type='Finalize Request',
        target_change=f'Request #{req.request_id}',
        details=details
    )
    db.session.add(log)
    db.session.commit()

    return redirect(url_for('admin.requests_list'))

# --- MISSING FUNCTIONS ADDED BELOW ---

@admin_bp.route('/export/csv')
@login_required
def export_csv():
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('main.index'))

    def generate():
        data = StringIO()
        w = csv.writer(data)

        # Write CSV Header
        w.writerow(('Project ID', 'Title', 'Status', 'Fund Amount', 'Approval Date', 'Site'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Write Project Data
        projects = Project.query.join(Request).all()
        for p in projects:
            w.writerow((
                p.project_id,
                p.request.project_title,
                p.current_status,
                p.given_fund,
                p.approval_date,
                p.request.project_site
            ))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    # Return as a downloadable file
    response = Response(stream_with_context(generate()), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='projects_report.csv')
    return response

@admin_bp.route('/system-logs')
@login_required
def system_logs():
    if current_user.role not in ['admin', 'super_admin']:
        return redirect(url_for('main.index'))
        
    # Fetch all logs, newest first
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    # 1. Security Check
    if current_user.role != 'super_admin':
        flash('Only the Captain can deactivate users.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # 2. Get Reason from Form
    reason = request.form.get('reason')
    if not reason:
        flash('A reason is required to remove a member.', 'warning')
        return redirect(url_for('main.public_records'))

    user_to_delete = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user_to_delete.user_id == current_user.user_id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('main.public_records'))

    # 3. Perform Deactivation (Soft Delete)
    user_to_delete.is_active = False
    
    # Optional: Mark name as removed visually in DB (helps historical logs)
    # if "(Removed)" not in user_to_delete.name:
    #     user_to_delete.name = f"{user_to_delete.name} (Removed)"
    
    # 4. Log with Reason
    log = SystemLog(
        actor_id=current_user.user_id,
        action_type='Deactivate User',
        target_change=f'Member: {user_to_delete.name}', 
        details=f"Reason: {reason}"
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'User {user_to_delete.name} has been deactivated.', 'success')
    return redirect(url_for('main.public_records'))