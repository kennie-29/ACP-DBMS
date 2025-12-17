from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from ..models import SystemLog, User, Project, Request, ProjectUpdate # <--- Added Project, Request
from ..database import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'super_admin']:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('associate.dashboard'))
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/public-logs')
def public_logs():
    # 1. Staff Updates (User management)
    user_actions = ['Create User', 'Delete User', 'Deactivate User', 'Update User', 'Register', 'Register Staff', 'Login', 'Logout']
    staff_logs = SystemLog.query.filter(SystemLog.action_type.in_(user_actions))\
                                .order_by(SystemLog.timestamp.desc()).all()

    # 2. Fund & Request Updates (THIS IS THE IMPORTANT PART)
    # We include all the specific actions we added to the logs
    fund_actions = ['Create Request', 'Vote Cast', 'Approve Request', 'Reject Request', 'Finalize Request']
    fund_logs = SystemLog.query.filter(SystemLog.action_type.in_(fund_actions))\
                               .order_by(SystemLog.timestamp.desc()).all()

    # 3. Project Updates (Site & Expenses)
    project_logs = SystemLog.query.filter_by(action_type='Project Update')\
                                  .order_by(SystemLog.timestamp.desc()).all()

    return render_template('main/public_logs.html', 
                           staff_logs=staff_logs, 
                           fund_logs=fund_logs, 
                           project_logs=project_logs)

@main_bp.route('/public-records')
def public_records():
    # 1. Fetch Members (Existing logic)
    members = User.query.filter(User.role != 'super_admin').all()
    
    # 2. Fetch Projects (Existing logic - usually just Ongoing/Completed)
    projects = Project.query.join(Request).order_by(Project.approval_date.desc()).all()

    # 3. NEW: Fetch ALL Requests (Pending, Approved, Rejected)
    # We order by submission date so the newest are first
    all_requests = Request.query.order_by(Request.submission_date.desc()).all()

    # 4. Calculate Total Funds Released (Sum of given_fund for all projects)
    total_released = db.session.query(db.func.sum(Project.given_fund)).scalar() or 0.0

    return render_template('main/public_records.html', 
                           members=members, 
                           projects=projects,
                           all_requests=all_requests,
                           total_released=total_released) # <--- Pass this new variable

@main_bp.route('/project/<int:project_id>/history')
def project_history(project_id):
    # Fetch project or return 404 if not found
    project = Project.query.get_or_404(project_id)
    
    # Fetch all updates for this project, sorted by newest first
    updates = ProjectUpdate.query.filter_by(project_id=project_id)\
                                 .order_by(ProjectUpdate.date_posted.desc()).all()
    
    return render_template('main/project_history.html', project=project, updates=updates)