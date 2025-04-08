from datetime import datetime, timedelta
from flask import current_app
from models import Activity, Alert
from db import db

class ProductivityAlerts:
    def __init__(self, user):
        self.user = user
        self.thresholds = {
            'low_productivity': 40,
            'high_productivity': 80,
            'long_session': 120,  # minutes
            'break_needed': 90,   # minutes
            'focus_drop': 20      # percentage points
        }

    def check_alerts(self):
        alerts = []
        current_time = datetime.now()

        # Get recent activities
        recent_activities = Activity.query.filter(
            Activity.user_id == self.user.id,
            Activity.start_time >= current_time - timedelta(hours=24)
        ).order_by(Activity.start_time.desc()).all()

        if not recent_activities:
            return alerts

        # Check for low productivity
        recent_avg = sum(a.productivity_score or 0 for a in recent_activities[:5]) / 5
        if recent_avg < self.thresholds['low_productivity']:
            alerts.append(self._create_alert(
                'low_productivity',
                f'Your productivity has dropped to {recent_avg:.1f}%. Consider taking a break.',
                'warning'
            ))

        # Check for sustained high productivity
        if recent_avg > self.thresholds['high_productivity']:
            alerts.append(self._create_alert(
                'high_productivity',
                f'Great work! You\'ve maintained {recent_avg:.1f}% productivity.',
                'success'
            ))

        # Check for long work sessions
        latest_activity = recent_activities[0]
        session_duration = (current_time - latest_activity.start_time).total_seconds() / 60
        if session_duration > self.thresholds['long_session']:
            alerts.append(self._create_alert(
                'long_session',
                f'You\'ve been working for {session_duration:.0f} minutes. Consider taking a break.',
                'warning'
            ))

        # Check for break needed
        if len(recent_activities) >= 2:
            time_since_break = (recent_activities[0].end_time - recent_activities[1].start_time).total_seconds() / 60
            if time_since_break > self.thresholds['break_needed']:
                alerts.append(self._create_alert(
                    'break_needed',
                    'You haven\'t taken a significant break. Consider resting for a few minutes.',
                    'warning'
                ))

        # Check for sudden productivity drops
        if len(recent_activities) >= 3:
            current_score = recent_activities[0].productivity_score or 0
            previous_avg = sum(a.productivity_score or 0 for a in recent_activities[1:4]) / 3
            if (previous_avg - current_score) > self.thresholds['focus_drop']:
                alerts.append(self._create_alert(
                    'focus_drop',
                    f'Your focus has dropped by {(previous_avg - current_score):.1f}%. Need help?',
                    'warning'
                ))

        return alerts

    def _create_alert(self, alert_type, message, severity):
        # Check if a similar alert was created recently
        recent_alert = Alert.query.filter(
            Alert.user_id == self.user.id,
            Alert.alert_type == alert_type,
            Alert.created_at >= datetime.now() - timedelta(hours=1)
        ).first()

        if not recent_alert:
            alert = Alert(
                user_id=self.user.id,
                alert_type=alert_type,
                message=message,
                severity=severity
            )
            db.session.add(alert)
            db.session.commit()
            return alert

        return None

    def get_active_alerts(self):
        # Get alerts from the last 24 hours
        return Alert.query.filter(
            Alert.user_id == self.user.id,
            Alert.created_at >= datetime.now() - timedelta(hours=24),
            Alert.dismissed == False
        ).order_by(Alert.created_at.desc()).all()

    def dismiss_alert(self, alert_id):
        alert = Alert.query.get(alert_id)
        if alert and alert.user_id == self.user.id:
            alert.dismissed = True
            db.session.commit()
            return True
        return False
