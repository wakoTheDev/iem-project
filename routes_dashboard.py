from flask import Blueprint, jsonify, request, url_for,redirect
from flask_login import login_required, current_user
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression
from .models import db, User, Task, Attendance
from .models_enhanced import EmployeeFeedback, ProductivityMetrics, DigitalActivity, Collaboration

dashboard = Blueprint('dashboard', __name__, url_prefix='/api/v2')

@dashboard.route('/productivity', methods=['GET', 'POST'])
@login_required
def handle_productivity():
    if request.method == 'POST':
        data = request.get_json()
        metrics = ProductivityMetrics(
            user_id=current_user.id,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            tasks_completed=data['tasks_completed'],
            efficiency_score=calculate_efficiency_score(data),
            focus_time=data['focus_time'],
            distractions=data['distractions']
        )
        db.session.add(metrics)
        db.session.commit()
        return jsonify({'message': 'Productivity recorded'}), 201
    else:
        # Get metrics for dashboard
        metrics = ProductivityMetrics.query.filter_by(user_id=current_user.id).all()
        digital_activity = DigitalActivity.query.filter_by(user_id=current_user.id).all()
        
        # Process into dashboard format
        return jsonify({
            'efficiency_score': calculate_current_efficiency(current_user.id),
            'tasks_completed': sum(m.tasks_completed for m in metrics[-7:]),
            'focus_time': sum(m.focus_time for m in metrics[-7:]),
            'engagement_score': calculate_engagement_score(current_user.id),
            'productivity_chart': format_productivity_chart(metrics),
            'app_usage_chart': format_app_usage(digital_activity),
            'recent_activities': get_recent_activities(current_user.id)
        })

def calculate_efficiency_score(data):
    # AI-powered efficiency scoring algorithm
    tasks_weight = 0.4
    focus_weight = 0.5
    distractions_weight = -0.1
    base_score = 50  # Average score
    
    score = base_score + \
            (data['tasks_completed'] * tasks_weight) + \
            (data['focus_time'] * focus_weight) + \
            (data['distractions'] * distractions_weight)
    return max(0, min(100, score))  # Clamp between 0-100

def calculate_current_efficiency(user_id):
    # Calculate weighted efficiency score
    metrics = ProductivityMetrics.query.filter_by(user_id=user_id).order_by(ProductivityMetrics.date.desc()).limit(7).all()
    if not metrics:
        return 0
    
    weights = [0.4, 0.3, 0.2, 0.1]  # Weight recent days more heavily
    weighted_sum = sum(m.efficiency_score * (weights[i] if i < len(weights) else 0.05) 
                      for i, m in enumerate(metrics))
    total_weight = sum(weights[:min(len(weights), len(metrics))])
    return round(weighted_sum / total_weight, 1)

def calculate_engagement_score(user_id):
    # Calculate based on feedback and collaboration metrics
    feedback = EmployeeFeedback.query.filter_by(user_id=user_id).all()
    collab = Collaboration.query.filter_by(user_id=user_id).all()
    
    if not feedback:
        return 0
        
    avg_feedback = sum(f.satisfaction_score for f in feedback) / len(feedback)
    collab_score = min(1, len(collab) / 5) * 20  # Max 20 points for collaboration
    
    return min(100, round(avg_feedback * 20 + collab_score + 50))  # Base 50 + feedback + collab

def format_productivity_chart(metrics):
    # Format data for Chart.js
    return {
        'labels': [m.date.strftime('%m/%d') for m in metrics[-7:]],
        'datasets': [{
            'label': 'Efficiency',
            'data': [m.efficiency_score for m in metrics[-7:]],
            'borderColor': '#3b82f6',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)'
        }]
    }

def format_app_usage(activities):
    # Group by application category
    categories = {}
    for act in activities:
        categories[act.category] = categories.get(act.category, 0) + act.duration
    
    return {
        'labels': list(categories.keys()),
        'datasets': [{
            'data': list(categories.values()),
            'backgroundColor': [
                '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'
            ]
        }]
    }

def get_recent_activities(user_id):
    # Combine recent tasks, attendance, and digital activity
    activities = []
    
    # Add recent tasks
    tasks = Task.query.filter_by(assigned_to=user_id).order_by(Task.due_date.desc()).limit(3).all()
    activities.extend({
        'type': 'task',
        'title': f'Task: {t.title}',
        'timestamp': t.due_date.strftime('%m/%d %H:%M'),
        'details': f'Status: {t.status}'
    } for t in tasks)
    
    # Add digital activity
    digital = DigitalActivity.query.filter_by(user_id=user_id).order_by(DigitalActivity.timestamp.desc()).limit(3).all()
    activities.extend({
        'type': 'digital',
        'title': f'Used {d.application}',
        'timestamp': d.timestamp.strftime('%m/%d %H:%M'),
        'details': f'{d.duration} mins ({d.category})'
    } for d in digital)
    
    return sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:5]

# Admin dashboard endpoints
@dashboard.route('/profile')
@login_required
def dashboard_profile():
    return redirect(url_for('dashboard.dashboard_profile'))

@dashboard.route('/admin/team-metrics')
@login_required
def get_team_metrics():
    if current_user.role not in ['manager', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Predictive analytics using simple linear regression
    user_data = ProductivityMetrics.query.all()
    dates = [d.date.toordinal() for d in user_data]
    scores = [d.efficiency_score for d in user_data]
    
    if len(dates) > 1:
        model = LinearRegression()
        model.fit(np.array(dates).reshape(-1,1), scores)
        future_date = datetime.now().toordinal() + 7  # Predict next week
        prediction = model.predict([[future_date]])[0]
    else:
        prediction = None
        
    return jsonify({
        'current_metrics': [m.to_dict() for m in user_data],
        'prediction': prediction
    })
