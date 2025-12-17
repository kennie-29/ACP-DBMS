from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = 'test'

# Mock user
class MockUser:
    role = 'super_admin'
    name = 'Test Admin'
    is_authenticated = True

@app.context_processor
def inject_user():
    return dict(current_user=MockUser())

@app.route('/')
def test_dashboard():
    # Mock data
    projects = []
    
    return render_template('admin/dashboard.html',
                           total_projects=10,
                           approved_projects=5,
                           pending_requests=2,
                           total_funds=50000,
                           ongoing_funds=20000,
                           completed_funds=30000,
                           projects=projects)

if __name__ == '__main__':
    with app.test_request_context():
        output = test_dashboard()
        print(output)
