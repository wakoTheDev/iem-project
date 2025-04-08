from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
import json
from models import User, Task, Attendance

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///productivity.db'
db = SQLAlchemy(app)

class ProductivityAnalytics:
    def __init__(self, db):
        self.db = db

    def get_user_productivity(self, user_id):
        # Get user's productivity metrics
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}

        # Get recent tasks
        tasks = Task.query.filter_by(assigned_to=user_id).order_by(Task.created_at.desc()).limit(5).all()
        
        # Get attendance
        attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.created_at.desc()).limit(5).all()
        
        return {
            'user': {
                'name': user.name,
                'department': user.department,
                'position': user.position
            },
            'tasks': [{'title': t.title, 'status': t.status, 'priority': t.priority} for t in tasks],
            'attendance': [{'date': a.created_at.strftime('%Y-%m-%d'), 'status': a.status} for a in attendance]
        }

    def calculate_real_time_stats(self):
        # Get real-time statistics
        active_users = User.query.filter_by(is_active=True).count()
        pending_tasks = Task.query.filter_by(status='pending').count()
        
        return {
            'active_users': active_users,
            'pending_tasks': pending_tasks,
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_active_users(self):
        # Get users who were active in the last 24 hours
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        active_users = User.query.filter(
            User.last_login >= twenty_four_hours_ago
        ).count()
        
        return active_users

@app.route('/productivity', methods=['GET'])
def get_productivity():
    analytics = ProductivityAnalytics(db)
    user_id = 1  # Replace with actual user ID
    metrics = analytics.get_user_productivity(user_id)
    return jsonify(metrics)

@app.route('/real-time-stats', methods=['GET'])
def get_real_time_stats():
    analytics = ProductivityAnalytics(db)
    stats = analytics.calculate_real_time_stats()
    return jsonify(stats)

@app.route('/active-users', methods=['GET'])
def get_active_users():
    analytics = ProductivityAnalytics(db)
    active_users = analytics.get_active_users()
    return jsonify({'active_users': active_users})

if __name__ == '__main__':
    app.run(debug=True)
