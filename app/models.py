from .database import db
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'head', 'admin', 'associate'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Merged Member Fields
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50))
    occupation = db.Column(db.String(50))
    relation_to_admin = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(50))
    pic_path = db.Column(db.String(100))

    # Relationships
    requests_made = db.relationship('Request', backref='requester', lazy=True)
    votes_cast = db.relationship('AdminVote', backref='admin', lazy=True)
    logs = db.relationship('SystemLog', backref='actor', lazy=True)
    updates_posted = db.relationship('ProjectUpdate', backref='poster', lazy=True)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Request(db.Model):
    __tablename__ = 'requests'

    request_id = db.Column(db.Integer, primary_key=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    project_title = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    fund_amount = db.Column(db.Float, nullable=False)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    project_site = db.Column(db.String(50), nullable=False)
    project_partners = db.Column(db.String(50), nullable=False)
    
    submission_date = db.Column(db.DateTime, default=datetime.now) # <--- UPDATED to System Time
    status = db.Column(db.String(20), default='Pending', nullable=False) # 'Pending', 'Approved', 'Rejected'

    # Relationships
    votes = db.relationship('AdminVote', backref='request', lazy=True)
    project = db.relationship('Project', backref='request', uselist=False, lazy=True)

class AdminVote(db.Model):
    __tablename__ = 'admin_votes'

    vote_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.request_id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    vote = db.Column(db.String(10), nullable=False) # 'Approve' or 'Reject'
    remarks = db.Column(db.String(255))

class Project(db.Model):
    __tablename__ = 'projects'

    project_id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.request_id'), unique=True, nullable=False)
    
    current_status = db.Column(db.String(50), nullable=False)
    given_fund = db.Column(db.Float, nullable=False)
    approval_date = db.Column(db.DateTime, default=datetime.now) # <--- UPDATED to System Time

    updates = db.relationship('ProjectUpdate', backref='project', lazy=True)
    comments = db.relationship('ProjectComment', backref='project', lazy=True, order_by="desc(ProjectComment.timestamp)")

    @property
    def is_overdue(self):
        """Returns True if the project is still 'Ongoing' but passed its End Date."""
        if self.current_status == 'Ongoing' and self.request.end_date:
            return date.today() > self.request.end_date
        return False

class ProjectUpdate(db.Model):
    __tablename__ = 'project_updates'

    update_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    update_title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    expenses = db.Column(db.Float, nullable=False)
    
    receipt_picture = db.Column(db.String(50))
    site_picture = db.Column(db.String(50))
    date_posted = db.Column(db.DateTime, default=datetime.now) # <--- UPDATED to System Time

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    action_type = db.Column(db.String(50), nullable=False) # e.g., 'Login', 'Vote'
    target_change = db.Column(db.String(50)) # e.g., 'Request #5'
    details = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.now) # <--- UPDATED to System Time

class ProjectComment(db.Model):
    __tablename__ = 'project_comments'

    comment_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
    
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    is_anonymous = db.Column(db.Boolean, default=True)

    # Relationship to project
    # Note: We can access project.comments if we add a backref to Project, or just query it directly.
    # Let's add a backref to Project for convenience.
