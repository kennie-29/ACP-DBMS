from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Request, Project, ProjectUpdate, SystemLog
from ..database import db

associate_bp = Blueprint('associate', __name__)

@associate_bp.route('/dashboard')
@login_required
def dashboard():
    # Ensure only associates (or non-admins) access this
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))

    # 1. Fetch My Requests
    my_requests = Request.query.filter_by(requested_by_user_id=current_user.user_id).all()
    
    # 2. Fetch My Active Projects (via Requests)
    # This joins Project and Request to find projects started by this user
    my_projects = Project.query.join(Request).filter(Request.requested_by_user_id == current_user.user_id).all()

    return render_template('associate/dashboard.html', requests=my_requests, projects=my_projects)

@associate_bp.route('/project/<int:project_id>/update', methods=['GET', 'POST'])
@login_required
def post_update(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Security check: Ensure the current user actually owns this project's request
    if project.request.requested_by_user_id != current_user.user_id:
        flash('You are not authorized to update this project.', 'danger')
        return redirect(url_for('associate.dashboard'))

    if request.method == 'POST':
        title = request.form.get('update_title')
        description = request.form.get('description')
        expenses = request.form.get('expenses')
        
        # TODO: Handle File Uploads (pictures) here later
        # receipt_pic = request.files['receipt']
        
        update = ProjectUpdate(
            project_id=project.project_id,
            posted_by=current_user.user_id,
            update_title=title,
            description=description,
            expenses=float(expenses) if expenses else 0.0,
            date_posted=datetime.utcnow()
        )
        
        db.session.add(update)
        db.session.commit()
        
        flash('Project update posted successfully!', 'success')
        return redirect(url_for('associate.dashboard'))

    return render_template('associate/post_update.html', project=project)