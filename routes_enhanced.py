from flask import Blueprint, jsonify, request
from models import db, User
from models_enhanced import EmployeeFeedback, ProductivityMetrics, DigitalActivity, Collaboration
from flask_login import login_required, current_user
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression

enhanced = Blueprint('enhanced', __name__)

# Employee Dashboard Endpoints
@enhanced.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    data = request.get_json()
    new_feedback = EmployeeFeedback(
        user_id=current_user.id,
        satisfaction_score=data['score'],
        feedback_text=data.get('text', ''),
        is_anonymous=data.get('anonymous', False)
    )
    db.session.add(new_feedback)
    db.session.commit()
    return jsonify({'message': 'Feedback submitted successfully'}), 201

@enhanced.route('/api/productivity', methods=['POST'])
@login_required
def record_productivity():
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

# Admin Dashboard Endpoints
@enhanced.route('/admin/team-metrics')
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

# Reporting Endpoints
@enhanced.route('/reports/daily')
@login_required
def daily_report():
    # Generate comprehensive daily report
    pass

# Helper methods
def generate_trend_analysis(user_id):
    # AI pattern detection implementation
    pass
