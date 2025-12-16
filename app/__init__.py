from flask import Flask
from .database import db  # <--- KEEP THIS: Import existing db instance
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail  # <--- Add Mail Import
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Initialize Extensions that don't need the app yet
# Note: db is already initialized in database.py
mail = Mail() 

def create_app():
    app = Flask(__name__)
    
    # --- 1. CONFIGURATION ---
    # Uses .env values if available, otherwise falls back to defaults
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///transparansee.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. EMAIL CONFIGURATION ---
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'sh4wntolentino@gmail.com' # <--- Update this
    app.config['MAIL_PASSWORD'] = 'dkff dbkm lifn vows'    # <--- Update this
    app.config['MAIL_DEFAULT_SENDER'] = 'sh4wntolentino@gmail.com'

    # --- 3. INITIALIZE EXTENSIONS ---
    db.init_app(app)       # Connects the imported db to this app
    Migrate(app, db)       # Enables 'flask db' commands
    mail.init_app(app)     # Connects mail to this app
    
    # --- 4. LOGIN MANAGER ---
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # Import User model for login manager
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
    # Note: Check if you want url_prefix='/requests' here or just root
    app.register_blueprint(request_bp) 
    app.register_blueprint(associate_bp, url_prefix='/associate')

    # --- 6. ERROR HANDLERS ---
    from .errors import register_error_handlers
    register_error_handlers(app)

    return app