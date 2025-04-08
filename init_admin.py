from app import app, db
from models import User

with app.app_context():
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(email='admin@felix.com').first()
    if not admin:
        admin = User(
            email='admin@felix.com',
            name='Admin User',
            department='Administration',
            position='System Administrator',
            role='admin',
            tier='premium'
        )
        admin.set_password('Admin@2025')  # Changed to meet password requirements
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists")
