import os
import time
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func

from ..models import Project, Request, ProjectUpdate, SystemLog
from ..database import db

associate_bp = Blueprint('associate', __name__)

# --- HELPER FUNCTION ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- DASHBOARD ROUTE ---
@associate_bp.route('/dashboard')
@login_required
def dashboard():
    # Security: Redirect Admins to their own dashboard
    if current_user.role in ['admin', 'super_admin']:
        return redirect(url_for('admin.dashboard'))

    # 1. Fetch My Requests
    my_requests = Request.query.filter_by(requested_by_user_id=current_user.user_id).all()
    
    # 2. Fetch My Active Projects
    my_projects = Project.query.join(Request).filter(Request.requested_by_user_id == current_user.user_id).all()

    # 3. Calculate Funds & Deadlines
    today = datetime.utcnow().date()
    
    for p in my_projects:
        # A. Calculate Remaining Fund
        # Sum up the 'expenses' column for this project from the updates table
        total_expenses = db.session.query(func.sum(ProjectUpdate.expenses))\
            .filter(ProjectUpdate.project_id == p.project_id).scalar() or 0.0
        
        # Attach temporary variables to the project object (for HTML use)
        p.total_expenses = total_expenses
        p.remaining_fund = p.given_fund - total_expenses
        
        # B. Check Deadline Warning
        if p.request.end_date:
            days_left = (p.request.end_date - today).days
            p.days_left = days_left
            
            # REMOVED: p.is_overdue = days_left < 0 
            # The 'Project' model now handles is_overdue automatically as a @property.
            
            # Mark as 'Urgent' if ending within 7 days and still Ongoing
            p.is_urgent = (0 <= days_left <= 7) and (p.current_status == 'Ongoing')
        else:
            p.days_left = 999 # Safe fallback if no date set
            p.is_urgent = False

    return render_template('associate/dashboard.html', requests=my_requests, projects=my_projects)


# --- POST UPDATE ROUTE (With Validation & Logging) ---
@associate_bp.route('/project/<int:project_id>/update/<string:type>', methods=['GET', 'POST'])
@login_required
def post_update(project_id, type):
    project = Project.query.get_or_404(project_id)
    
    # 1. Authorization Check (User must own the project)
    if project.request.requested_by_user_id != current_user.user_id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('associate.dashboard'))

    # 2. Deadline Enforcement
    today = datetime.utcnow().date()
    if project.request.end_date and today > project.request.end_date:
        flash('Cannot post update: The project deadline has passed.', 'danger')
        return redirect(url_for('associate.dashboard'))

    # 3. Handle Form Submission
    if request.method == 'POST':
        title = request.form.get('update_title')
        description = request.form.get('description')
        
        expenses_amount = 0.0
        
        # --- BUDGET PROTECTION CHECK ---
        if type == 'expense':
            expenses_amount = float(request.form.get('expenses') or 0.0)
            
            # Calculate total previously spent
            current_spent = db.session.query(func.sum(ProjectUpdate.expenses))\
                .filter(ProjectUpdate.project_id == project.project_id).scalar() or 0.0
            
            # Calculate Remaining Balance
            remaining_balance = project.given_fund - current_spent
            
            # Check if new expense exceeds balance
            if expenses_amount > remaining_balance:
                flash(f'Expense rejected! You only have ₱{remaining_balance:,.2f} remaining.', 'danger')
                
                # RE-RENDER TEMPLATE (Do not redirect)
                return render_template('associate/post_update.html', 
                                     project=project, 
                                     type=type, 
                                     error_field='expenses')
        # -------------------------------

        # 4. File Upload Logic
        receipt_file_name = None
        site_file_name = None
        
        file = request.files.get('file_upload')
        if file and allowed_file(file.filename):
            # Shorten/Secure filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            timestamp = int(time.time())
            # Format: type_timestamp.ext (e.g., site_17000123.jpg)
            final_filename = f"{type}_{timestamp}.{ext}"
            
            # Decide folder: 'static/project_updates/receipts' OR 'static/project_updates/site_photos'
            subfolder = 'receipts' if type == 'expense' else 'site_photos'
            upload_path = os.path.join(current_app.root_path, 'static', 'project_updates', subfolder)
            
            # Create folder if it doesn't exist
            os.makedirs(upload_path, exist_ok=True)
            
            # Save file
            file.save(os.path.join(upload_path, final_filename))

            # Assign to correct DB column variable
            if type == 'expense':
                receipt_file_name = final_filename
            else:
                site_file_name = final_filename

        # 5. Save to Database
        # We automatically add the type to the title for clarity in the update table
        final_title = f"[{type.upper()}] {title}"
        
        update = ProjectUpdate(
            project_id=project.project_id,
            posted_by=current_user.user_id,
            update_title=final_title,
            description=description,
            expenses=expenses_amount,
            # We fill the correct column based on type
            receipt_picture=receipt_file_name, 
            site_picture=site_file_name,
            date_posted=datetime.utcnow()
        )
        
        db.session.add(update)
        db.session.commit()
        
        # 6. Log the Action (FORMATTED FOR TRANSPARENCY LOGS)
        log_details = f"Type: {type.capitalize()} | Title: {title} | Desc: {description}"
        if expenses_amount > 0:
            log_details += f" | Expense: {expenses_amount}"

        log = SystemLog(
            actor_id=current_user.user_id,
            action_type='Project Update',
            # We use the Project Title here so it shows up nicely in the logs
            target_change=f'Project: {project.request.project_title}', 
            details=log_details
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'{type.capitalize()} update posted successfully!', 'success')
        return redirect(url_for('associate.dashboard'))

    return render_template('associate/post_update.html', project=project, type=type)