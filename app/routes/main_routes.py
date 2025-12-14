from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from ..models import SystemLog, User, Project, Request # <--- Added Project, Request
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

# --- NEW ROUTE FOR PUBLIC LOGS ---
@main_bp.route('/public-logs')
def public_logs():
    # Group 1: Admin and Staff Creation/Deletion/Edit
    # UPDATE: Added 'Deactivate User' so removal logs appear here
    user_actions = ['Create User', 'Delete User', 'Deactivate User', 'Update User', 'Register']
    
    staff_logs = SystemLog.query.filter(SystemLog.action_type.in_(user_actions))\
                                .order_by(SystemLog.timestamp.desc()).all()

    # Group 2: Fund Requests, Status, Processing
    fund_actions = ['Create Request', 'Approve Request', 'Reject Request', 'Finalize Request', 'Vote Cast']
    
    fund_logs = SystemLog.query.filter(SystemLog.action_type.in_(fund_actions))\
                               .order_by(SystemLog.timestamp.desc()).all()

    return render_template('main/public_logs.html', staff_logs=staff_logs, fund_logs=fund_logs)

@main_bp.route('/public-records')
def public_records():
    # 1. Fetch Members: Showing Admins and Associates
    #    We fetch ALL (even deactivated ones) so the "Removed" badge logic works in the HTML
    members = User.query.filter(User.role.in_(['admin', 'associate'])).order_by(User.role).all()
    
    # 2. Fetch Projects: Join with Request to get titles/site info
    #    We show all projects except Cancelled ones
    projects = Project.query.join(Request).filter(Project.current_status != 'Cancelled').all()
    
    return render_template('main/public_records.html', members=members, projects=projects)