from flask import Flask
from .database import db
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    # Uses .env values if available, otherwise falls back to defaults
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///transparansee.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Extensions
    db.init_app(app)
    Migrate(app, db)  # This enables 'flask db' commands
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # Import User model for login manager
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    # NOTE: These imports might crash initially because the route files 
    # are likely still referring to old models (like MemberRecord). 
    # We will fix the route files in the next step.
    from .routes.main_routes import main_bp
    from .routes.auth_routes import auth_bp
    from .routes.admin_routes import admin_bp
    from .routes.request_routes import request_bp
    from .routes.associate_routes import associate_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(request_bp)
    app.register_blueprint(associate_bp)

    # Error Handlers
    from .errors import register_error_handlers
    register_error_handlers(app)

    return app