from app import app, db
from models import User

with app.app_context():
    # Check if admin exists
    admin = User.query.filter_by(email='admin@felix.com').first()
    if admin:
        print(f"Admin user exists: {admin}")
        print(f"Password hash: {admin.password_hash}")
    else:
        print("Admin user not found")
