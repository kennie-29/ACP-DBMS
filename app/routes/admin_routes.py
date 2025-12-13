from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..utils.decorators import admin_required
from ..models import Project, Request, User, SystemLog, AdminVote
from ..database import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # 1. Analytics
    total_projects = Project.query.count()
    approved_projects = Project.query.filter(Project.current_status != 'Cancelled').count()
    # New Logic: Count requests where status is 'Pending'
    pending_requests = Request.query.filter_by(status='Pending').count()
    
    # Calculate Total Funds (sum of given_fund)
    total_funds = db.session.query(db.func.sum(Project.given_fund)).scalar() or 0.0

    # 2. Recent Activity (Projects)
    search_query = request.args.get('q', '').lower()
    
    # Fetch all projects joined with Request to access titles
    query = Project.query.join(Request).order_by(Project.approval_date.desc())
    
    if search_query:
        # Filter by Project Title or Site (accessed via the Request relationship)
        query = query.filter(
            (Request.project_title.ilike(f'%{search_query}%')) | 
            (Request.project_site.ilike(f'%{search_query}%'))
        )
        
    projects = query.all()

    return render_template('admin/dashboard.html', 
                           total_projects=total_projects,
                           approved_projects=approved_projects,
                           pending_requests=pending_requests,
                           total_funds=total_funds,
                           projects=projects)

@admin_bp.route('/requests')
@login_required
@admin_required
def requests_list():
    # Fetch all requests that are still Pending
    requests = Request.query.filter_by(status='Pending').all()
    return render_template('admin/requests_list.html', requests=requests)

@admin_bp.route('/register-associate', methods=['GET', 'POST'])
@login_required
@admin_required
def register_associate():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email') # New required field
        password = request.form.get('password')
        name = request.form.get('name')
        occupation = request.form.get('occupation')
        address = request.form.get('address')
        relation = request.form.get('relation')
        
        # Validation
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.register_associate'))
            
        # Create User (Associate)
        new_user = User(
            username=username,
            email=email,
            role='associate',
            name=name,
            occupation=occupation,
            address=address,
            relation_to_admin=relation,
            pic_path='default.jpg'
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log this action
        log = SystemLog(
            actor_id=current_user.user_id,
            action_type='Create User',
            target_change=f'User {new_user.username}',
            details='Registered new associate'
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Associate {name} registered successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin/register_associate.html')

@admin_bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_request(request_id):
    req = Request.query.get_or_404(request_id)
    remarks = request.form.get('remarks')  # <--- CAPTURE REMARKS
    
    # 1. Update Request Status
    req.status = 'Approved'
    
    # 2. Record the Admin's Vote (with Remarks)
    vote = AdminVote(
        request_id=req.request_id,
        admin_id=current_user.user_id,
        vote='Approve',
        remarks=remarks  # <--- SAVE HERE
    )
    db.session.add(vote)
    
    # 3. Create Project
    proj = Project(
        request_id=req.request_id,
        current_status='Ongoing',
        given_fund=req.fund_amount,
        approval_date=datetime.utcnow()
    )
    db.session.add(proj)
    
    # 4. System Log
    log = SystemLog(
        actor_id=current_user.user_id,
        action_type='Approve Request',
        target_change=f'Request #{req.request_id}',
        details=f'Approved with remarks: {remarks}'
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash('Request approved successfully!', 'success')
    return redirect(url_for('admin.requests_list'))

@admin_bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_request(request_id):
    req = Request.query.get_or_404(request_id)
    remarks = request.form.get('remarks') # <--- CAPTURE REMARKS

    req.status = 'Rejected'
    
    vote = AdminVote(
        request_id=req.request_id,
        admin_id=current_user.user_id,
        vote='Reject',
        remarks=remarks
    )
    db.session.add(vote)
    
    log = SystemLog(
        actor_id=current_user.user_id,
        action_type='Reject Request',
        target_change=f'Request #{req.request_id}',
        details=f'Rejected with remarks: {remarks}'
    )
    db.session.add(log)
    
    db.session.commit()
    
    flash('Request rejected.', 'warning')
    return redirect(url_for('admin.requests_list'))
@admin_bp.route('/system-logs')
@login_required
@admin_required
def system_logs():
    # Fetch all logs, newest first
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/export/csv')
@login_required
@admin_required
def export_csv():
    # NOTE: You will need to update your project_service.py to match 
    # the new table column names (e.g. project_title instead of proj_title)
    from ..services.project_service import ProjectService
    import os
    from flask import send_file, current_app
    
    try:
        service = ProjectService(upload_folder=os.path.join(current_app.root_path, 'static', 'exports'))
        os.makedirs(service.upload_folder, exist_ok=True)
        
        filepath = service.export_projects_to_csv()
        return send_file(filepath, as_attachment=True, download_name='projects_report.csv')
    except Exception as e:
        flash(f"Export Failed: {str(e)}", 'danger')
        return redirect(url_for('admin.dashboard'))