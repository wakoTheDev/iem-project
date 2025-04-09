from datetime import datetime
from .models import db

class EmployeeFeedback(db.Model):
    __tablename__ = 'employee_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    satisfaction_score = db.Column(db.Integer, nullable=False)
    feedback_text = db.Column(db.Text)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=False)

class ProductivityMetrics(db.Model):
    __tablename__ = 'productivity_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0)
    efficiency_score = db.Column(db.Float)
    focus_time = db.Column(db.Float)
    distractions = db.Column(db.Integer)

class DigitalActivity(db.Model):
    __tablename__ = 'digital_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    application = db.Column(db.String(100))
    category = db.Column(db.String(50))
    duration = db.Column(db.Float)
    productivity_score = db.Column(db.Float)

class ProductivityAnalytics:
    def __init__(self, db):
        self.db = db

    def get_user_productivity(self, user_id):
        metrics = ProductivityMetrics.query.filter_by(user_id=user_id).all()
        # Calculate and return productivity metrics
        # This is a placeholder for actual calculation logic
        return {
            "tasks_completed": sum(metric.tasks_completed for metric in metrics),
            "efficiency_score": sum(metric.efficiency_score for metric in metrics) / len(metrics) if metrics else 0,
            "focus_time": sum(metric.focus_time for metric in metrics),
            "distractions": sum(metric.distractions for metric in metrics),
        }

    def calculate_real_time_stats(self):
        # Placeholder for real-time stats calculation logic
        return {
            "active_users": 10,  # Example static value
            "average_efficiency": 75.0  # Example static value
        }

class Collaboration(db.Model):
    __tablename__ = 'collaboration'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    meetings_attended = db.Column(db.Integer)
    messages_sent = db.Column(db.Integer)
    documents_shared = db.Column(db.Integer)
    collaboration_score = db.Column(db.Float)
