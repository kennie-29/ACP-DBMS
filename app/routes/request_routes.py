from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Request, SystemLog  # <--- Ensure SystemLog is imported
from ..database import db

request_bp = Blueprint('request', __name__)

@request_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_request():
    # Security Check
    if current_user.role != 'associate':
        flash('Only staff associates can submit funding requests.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # 1. GET DATA
        title = request.form.get('project_title')
        site = request.form.get('project_site')
        partners = request.form.get('project_partners') # <--- We need to save this!
        reason = request.form.get('reason')
        amount = request.form.get('fund_amount')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # 2. VALIDATION
        # Added 'partners' to the check since the DB requires it
        if not all([title, site, reason, amount, start_date_str, end_date_str, partners]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('requests/create_request.html')

        try:
            amount_float = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return render_template('requests/create_request.html')

        # 3. DATE PARSING
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('requests/create_request.html')

        # 4. SAVE TO DATABASE
        new_request = Request(
            requested_by_user_id=current_user.user_id,
            project_title=title,
            project_site=site,
            fund_amount=amount_float,
            reason=reason,             # <--- Just the reason (no need to combine anymore)
            project_partners=partners, # <--- THIS FIXES THE ERROR
            start_date=start_date_obj,
            end_date=end_date_obj,
            status='Pending',
            submission_date=datetime.utcnow()
        )
        
        db.session.add(new_request)
        db.session.commit()

        # 5. LOGGING
        log = SystemLog(
            actor_id=current_user.user_id,
            action_type='Create Request', 
            target_change=f'Request: {title}',
            details=f"Amount: ₱{amount_float:,.2f} | Site: {site}"
        )
        db.session.add(log)
        db.session.commit()

        flash('Funding proposal submitted successfully!', 'success')
        return redirect(url_for('associate.dashboard'))

    return render_template('requests/create_request.html')

@request_bp.route('/view/<int:request_id>')
@login_required
def view_request(request_id):
    # Fetch the request or show 404 error if not found
    req = Request.query.get_or_404(request_id)
    
    return render_template('requests/view_request.html', req=req)