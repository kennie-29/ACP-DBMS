from flask import Flask
from .database import db  # <--- KEEP THIS: Import existing db instance
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Extensions
mail = Mail() 

def create_app():
    app = Flask(__name__)
    
    # --- 1. CONFIGURATION ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///transparansee.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. EMAIL CONFIGURATION ---
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'sh4wntolentino@gmail.com' 
    app.config['MAIL_PASSWORD'] = 'dkff dbkm lifn vows'   
    app.config['MAIL_DEFAULT_SENDER'] = 'sh4wntolentino@gmail.com'

    # --- 3. INITIALIZE EXTENSIONS ---
    db.init_app(app)
    Migrate(app, db)
    mail.init_app(app)
    
    # --- 4. LOGIN MANAGER ---
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- 5. REGISTER BLUEPRINTS ---
    from .routes.main_routes import main_bp
    from .routes.auth_routes import auth_bp
    from .routes.admin_routes import admin_bp
    from .routes.request_routes import request_bp
    from .routes.associate_routes import associate_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(request_bp) 
    app.register_blueprint(associate_bp, url_prefix='/associate')

    # --- 6. CREATE DATABASE TABLES ---
    with app.app_context():
        # REMOVED 'Vote' from this list because you are using 'AdminVote'
        from .models import User, Request, Project, SystemLog, AdminVote, ProjectUpdate
        
        db.create_all()
        print("✅ Database tables checked/created successfully!")

    return app