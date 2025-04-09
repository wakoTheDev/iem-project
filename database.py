from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(id):
    from .models import User
    return User.query.get(int(id))

# Create the database tables
def init_db():
    db.create_all()

if __name__ == '__main__':
    from app import app
    db.init_app(app)
    init_db()
