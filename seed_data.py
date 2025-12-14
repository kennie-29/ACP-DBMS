from app import create_app, db
from app.models import User, Request, Project
from datetime import datetime

app = create_app()

with app.app_context():
    print("🌱 Seeding Data...")

    # 1. Create SUPER ADMIN (Barangay Captain)
    captain = User.query.filter_by(username='admin').first()
    if not captain:
        captain = User(
            username='admin',
            email='captain@barangay.gov',
            role='super_admin',
            name='Kapitan Tiago',
            occupation='Barangay Captain',
            address='Barangay Hall, Main Office',
            relation_to_admin='Self',
            pic_path='default.png',
            is_active=True
        )
        captain.set_password('admin123')
        db.session.add(captain)
        print("✅ Super Admin (Captain) created: admin / admin123")

    # 2. Create OFFICER (Admin who votes)
    officer = User.query.filter_by(username='officer1').first()
    if not officer:
        officer = User(
            username='officer1',
            email='officer1@barangay.gov',
            role='admin',
            name='Kagawad Juan',
            occupation='Barangay Kagawad',
            address='Purok 1, Street 2',
            relation_to_admin='Councilor',
            pic_path='default.png',
            is_active=True
        )
        officer.set_password('password123')
        db.session.add(officer)
        print("✅ Officer created: officer1 / password123")

    # 3. Create ASSOCIATE (Researcher who requests funds)
    researcher = User.query.filter_by(username='researcher1').first()
    if not researcher:
        researcher = User(
            username='researcher1',
            email='researcher@gmail.com',
            role='associate',
            name='Maria Clara',
            occupation='Project Lead',
            address='Purok 5, Riverside',
            relation_to_admin='None',
            pic_path='default.png',
            is_active=True
        )
        researcher.set_password('password123')
        db.session.add(researcher)
        print("✅ Associate created: researcher1 / password123")

    # Commit Users first so they get IDs
    db.session.commit()

    # 4. Create a Sample Completed Project (For Public Records)
    # We need to fetch the user object again to get the ID safely
    requester = User.query.filter_by(username='researcher1').first()
    
    if requester:
        existing_request = Request.query.filter_by(project_title="Street Light Installation").first()
        if not existing_request:
            # Create Request
            sample_req = Request(
                requested_by_user_id=requester.user_id,
                project_title="Street Light Installation",
                reason="To improve safety in Purok 3 at night.",
                fund_amount=50000.0,
                project_site="Purok 3",
                project_partners="Electric Coop",
                start_date=datetime.utcnow().date(),
                end_date=datetime.utcnow().date(),
                status='Approved'
            )
            db.session.add(sample_req)
            db.session.commit() # Commit to generate request_id

            # Create Project
            sample_proj = Project(
                request_id=sample_req.request_id,
                current_status='Completed',
                given_fund=50000.0,
                approval_date=datetime.utcnow()
            )
            db.session.add(sample_proj)
            print("✅ Sample Project created: Street Light Installation")

    db.session.commit()
    print("🚀 Database seeded successfully!")