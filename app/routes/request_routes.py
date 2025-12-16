from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Request, SystemLog  # <--- Ensure SystemLog is imported
from ..database import db

request_bp = Blueprint('request', __name__)

# In app/routes/request_routes.py

@request_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_request():
    # Security Check
    if current_user.role != 'associate':
        flash('Only staff associates can submit funding requests.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # 1. GET DATA using the names from YOUR HTML
        title = request.form.get('project_title')       # Matches <input name="project_title">
        site = request.form.get('project_site')         # Matches <input name="project_site">
        partners = request.form.get('project_partners') # Matches <input name="project_partners">
        reason = request.form.get('reason')             # Matches <textarea name="reason">
        amount = request.form.get('fund_amount')        # Matches <input name="fund_amount">
        start_date = request.form.get('start_date')     # Matches <input name="start_date">
        end_date_str = request.form.get('end_date')     # Matches <input name="end_date">

        # 2. VALIDATION
        if not all([title, site, reason, amount]):
            flash('Please fill in all required fields.', 'warning')
            return render_template('request/create_request.html')

        # 3. COMBINE EXTRA FIELDS (Optional)
        # Since your DB might not have 'partners' or 'start_date' columns yet, 
        # we can append them to the 'reason' so the info isn't lost.
        full_reason = f"{reason}\n\n[Partners: {partners}] [Proposed Start: {start_date}]"

        try:
            amount_float = float(amount)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return render_template('request/create_request.html')

        # Parse End Date
        end_date_obj = None
        if end_date_str:
            try:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # 4. SAVE TO DATABASE
        new_request = Request(
            requested_by_user_id=current_user.user_id,
            project_title=title,
            project_site=site,
            fund_amount=amount_float,
            reason=full_reason, # We save the combined info here
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