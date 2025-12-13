from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(role='admin').first()
    
    if admin:
        print(f"Admin already exists: {admin.username}")
    else:
        # Create the Super Admin
        new_admin = User(
            username='admin',
            email='admin@transparansee.com',
            role='admin',
            name='Super Administrator',
            occupation='System Owner',
            address='Headquarters',
            pic_path='default.jpg'
        )
        new_admin.set_password('admin123')  # <--- DEFAULT PASSWORD
        
        db.session.add(new_admin)
        db.session.commit()
        print("Success! Admin created.")
        print("Username: admin")
        print("Password: admin123")