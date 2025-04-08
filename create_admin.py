from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo
from models import User, Task, Attendance, Alert, AnalyticsData, Notification
from models_enhanced import EmployeeFeedback, ProductivityMetrics, DigitalActivity, Collaboration, ProductivityAnalytics
from database import db, login_manager, init_db
from routes_enhanced import enhanced
from routes_dashboard import dashboard
import os
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlparse

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'iem_system.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app)

with app.app_context():
    if not os.path.exists(db_path):
        print(f"Creating new database at: {db_path}")
        init_db()
    else:
        print(f"Using existing database at: {db_path}")

app.register_blueprint(enhanced, url_prefix='/v2')
app.register_blueprint(dashboard)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    theme = SelectField('Theme', choices=[('light', 'Light'), ('dark', 'Dark')])

class SignupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    department = StringField('Department', validators=[DataRequired()])
    position = StringField('Position', validators=[DataRequired()])

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            email = form.email.data.strip()
            password = form.password.data
            
            print(f"Received email: {email}")  # Debug print
            user = User.query.filter_by(email=email).first()
            if not user:
                print(f"User not found for email: {email}")  # Debug print
                if email == 'test@example.com':
                    print("Debug mode activated for test@example.com")  # Debug print
                    return f"DEBUG: User not found - {email}\nAll users: {[u.email for u in User.query.all()]}", 404
                flash('Invalid email or password', 'error')
                return render_template('login.html', form=form)
                
            print(f"Attempting login for: {email}")  # Debug
            print(f"Stored hash: {user.password}")  # Debug
            print(f"Password check result: {user.check_password(password)}")  # Debug
            
            if not user.check_password(password):
                flash('Invalid email or password', 'error')
                print("Password verification failed")  # Debug
                return render_template('login.html', form=form)
                
            login_user(user)
            print(f"Session after login: {session}")  # Debug session
            print(f"User authenticated: {current_user.is_authenticated}")  # Debug auth status
            
            user.last_login = datetime.utcnow()
            user.theme_preference = form.theme.data
            db.session.commit()
            
            flash('Logged in successfully!', 'success')
            print("Redirecting to dashboard...")  # Debug
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            app.logger.error(f'Login error: {str(e)}')
            if email == 'test@example.com':
                return f"DEBUG: Login error - {str(e)}", 500
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html', form=form)
    
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        try:
            email = form.email.data.strip()
            password = form.password.data
            name = form.name.data.strip()
            department = form.department.data.strip()
            position = form.position.data.strip()
            
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('An account with this email already exists', 'error')
                return render_template('auth/signup.html', form=form)
            
            user = User(email=email, name=name, department=department, position=position, role='employee', tier='free')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            app.logger.error(f'Signup error: {str(e)}')
            flash('An error occurred during signup. Please try again.', 'error')
            return render_template('auth/signup.html', form=form)
    
    return render_template('auth/signup.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        try:
            email = form.email.data.strip()
            user = User.query.filter_by(email=email).first()
            
            if user:
                reset_token = user.get_reset_token()
                send_reset_email(user, reset_token)
                flash('An email has been sent with instructions to reset your password.', 'info')
                return redirect(url_for('login'))
            else:
                flash('If an account exists with that email, you will receive an email with instructions to reset your password.', 'info')
                return redirect(url_for('login'))
                
        except Exception as e:
            app.logger.error(f'Password reset error: {str(e)}')
            flash('An error occurred while processing your request. Please try again.', 'error')
            return redirect(url_for('login'))
    
    return render_template('auth/forgt_password.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Your password has been updated! You are now able to log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f'Password reset error: {str(e)}')
            flash('An error occurred while resetting your password. Please try again.', 'error')
            return redirect(url_for('forgot_password'))
    
    return render_template('auth/reset_password.html', form=form)

def send_reset_email(user, token):
    try:
        with open('reset_email.txt', 'w') as f:
            f.write(f'''To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, please ignore this email.
''')
        
        with open('reset_email.txt', 'r') as f:
            content = f.read()
        
        os.remove('reset_email.txt')
        
        app.logger.info(f'Sending password reset email to {user.email}')
        print(f"\nPassword reset email content for {user.email}:")
        print(content)
        
    except Exception as e:
        app.logger.error(f'Email sending error: {str(e)}')
        raise

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        analytics = ProductivityAnalytics(db)
        
        if current_user.role == 'admin':
            active_users = User.query.filter(User.last_login >= datetime.utcnow() - timedelta(days=1)).all()
        else:
            active_users = [current_user]
        
        user_tasks = Task.query.filter_by(assigned_to=current_user.id).order_by(Task.due_date).all()
        recent_attendance = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.check_in.desc()).limit(5).all()
        
        alerts = Alert.query.filter_by(user_id=current_user.id, read=False).order_by(Alert.created_at.desc()).all()
        
        return render_template('dashboard.html', 
                             active_users=active_users,
                             tasks=user_tasks,
                             attendance=recent_attendance,
                             alerts=alerts)
        
    except Exception as e:
        app.logger.error(f'Dashboard error: {str(e)}')
        flash('An error occurred while loading the dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html')

@app.route('/contact/submit', methods=['POST'])
@login_required
def contact_submit():
    try:
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        message = request.form.get('message', '')
        
        if not all([name, email, message]):
            flash('All fields are required', 'error')
            return redirect(url_for('contact'))
            
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('contact'))
            
        print(f"New contact form submission:\nName: {name}\nEmail: {email}\nMessage: {message}")
        flash('Thank you for your message! We will get back to you soon.')
        return redirect(url_for('contact'))
        
    except Exception as e:
        app.logger.error(f'Error processing contact form: {str(e)}')
        flash('An error occurred while processing your request', 'error')
        return redirect(url_for('contact'))

@app.route('/notifications/<int:notification_id>/read')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('You cannot mark other user\'s notifications as read', 'error')
        return redirect(url_for('notifications'))
    
    notification.read = True
    db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/analytics')
@login_required
def analytics():
    try:
        user_analytics = AnalyticsData.query.filter_by(user_id=current_user.id).all()
        
        if current_user.role in ['manager', 'admin']:
            team_members = User.query.filter_by(department=current_user.department).all()
            team_analytics = []
            for member in team_members:
                member_analytics = AnalyticsData.query.filter_by(user_id=member.id).all()
                team_analytics.extend(member_analytics)
        
        return render_template('analytics.html', 
                             user_analytics=user_analytics,
                             team_analytics=team_analytics if current_user.role in ['manager', 'admin'] else None)
        
    except Exception as e:
        app.logger.error(f'Analytics error: {str(e)}')
        flash('An error occurred while loading analytics', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/reports')
@login_required
def get_reports():
    try:
        analytics = ProductivityAnalytics(db)
        reports = analytics.get_user_productivity(current_user.id)
        return jsonify(reports)
    except Exception as e:
        app.logger.error(f'Error getting reports: {str(e)}')
        return jsonify({'error': 'Failed to fetch reports'}), 500

@app.route('/api/real-time-stats')
@login_required
def get_real_time_stats():
    try:
        analytics = ProductivityAnalytics(db)
        stats = analytics.calculate_real_time_stats()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f'Error getting real-time stats: {str(e)}')
        return jsonify({'error': 'Failed to fetch real-time stats'}), 500

@app.route('/api/analytics/<int:user_id>')
@login_required
def get_user_analytics(user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        analytics = ProductivityAnalytics(db)
        data = analytics.get_user_productivity(user_id)
        return jsonify(data)
    except Exception as e:
        app.logger.error(f'Error getting user analytics: {str(e)}')
        return jsonify({'error': 'Failed to fetch analytics'}), 500

@app.route('/api/productivity')
@login_required
def get_user_productivity():
    try:
        analytics = ProductivityAnalytics(db)
        data = analytics.get_user_productivity(current_user.id)
        return jsonify(data)
    except Exception as e:
        app.logger.error(f'Error getting productivity: {str(e)}')
        return jsonify({'error': 'Failed to fetch productivity data'}), 500

@app.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    try:
        theme = request.json.get('theme')
        if theme not in ['light', 'dark']:
            return jsonify({'error': 'Invalid theme'}), 400
            
        current_user.theme_preference = theme
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f'Error updating theme: {str(e)}')
        return jsonify({'error': 'Failed to update theme'}), 500

@socketio.on('connect')
def handle_connect():
    try:
        if current_user.is_authenticated:
            current_user.last_active = datetime.utcnow()
            db.session.commit()
            emit('user_connected', {'user_id': current_user.id})
    except Exception as e:
        app.logger.error(f'SocketIO connect error: {str(e)}')

@socketio.on('disconnect')
def handle_disconnect():
    try:
        if current_user.is_authenticated:
            emit('user_disconnected', {'user_id': current_user.id})
    except Exception as e:
        app.logger.error(f'SocketIO disconnect error: {str(e)}')

@app.route('/test_login')
def test_login():
    user = User.query.filter_by(email='admin@felix.com').first()
    if user and user.check_password('Admin@1234'):
        login_user(user)
        return "Login successful!"
    return "Login failed"

if __name__ == '__main__':
    with app.app_context():
        try:
            admin = User.query.filter_by(email='admin@iem-system.com').first()
            if not admin:
                admin = User(
                    email='admin@iem-system.com',
                    name='Admin User',
                    department='IT',
                    position='System Administrator',
                    role='admin',
                    tier='premium'
                )
                admin.set_password('Admin@2025')
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
            
        except Exception as e:
            app.logger.error(f'Error during app startup: {str(e)}')
            
    socketio.run(app, debug=True)
