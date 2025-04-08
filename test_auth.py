from app import app
from models import User

with app.app_context():
    admin = User.query.filter_by(email='admin@felix.com').first()
    if admin:
        print("Testing password verification:")
        print(f"Password 'Admin@1234' valid: {admin.check_password('Admin@1234')}")
        print(f"Password 'wrongpass' valid: {admin.check_password('wrongpass')}")
    else:
        print("Admin user not found")
