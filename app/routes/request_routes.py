from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Request, SystemLog
from ..database import db

request_bp = Blueprint('request', __name__)

@request_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_request():
    if request.method == 'POST':
        # 1. Get Form Data
        title = request.form.get('project_title')
        reason = request.form.get('reason')
        amount = request.form.get('fund_amount')
        site = request.form.get('project_site')
        partners = request.form.get('project_partners')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # 2. Convert Dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('request.create_request'))

        # 3. Create Request Object
        new_req = Request(
            requested_by_user_id=current_user.user_id,
            project_title=title,
            reason=reason,
            fund_amount=float(amount),
            project_site=site,
            project_partners=partners,
            start_date=start_date,
            end_date=end_date,
            status='Pending'
        )

        db.session.add(new_req)
        db.session.commit()

        # 4. Log Action
        log = SystemLog(
            actor_id=current_user.user_id,
            action_type='Create Request',
            target_change=f'Request #{new_req.request_id}',
            details=f'Requested ${amount} for {title}'
        )
        db.session.add(log)
        db.session.commit()

        flash('Funding request submitted successfully!', 'success')
        
        # Redirect based on role
        if current_user.role == 'associate':
            return redirect(url_for('associate.dashboard'))
        return redirect(url_for('main.index'))

    return render_template('requests/create_request.html')

@request_bp.route('/<int:request_id>')
@login_required
def view_request(request_id):
    req = Request.query.get_or_404(request_id)
    return render_template('requests/view_request.html', req=req)