from flask import Flask, abort, request
from datetime import timedelta
import json, os, logging, sqlite3
from .blueprints.student import student_bp
from .blueprints.admin import admin_bp

def init_db():
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # Create table with enrollment_no column included
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id TEXT, roll_no TEXT, enrollment_no TEXT, dept TEXT, 
                  filename TEXT, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Migration safety: If an older table exists without 'enrollment_no', add it dynamically
    c.execute("PRAGMA table_info(submissions)")
    columns = [column[1] for column in c.fetchall()]
    if 'enrollment_no' not in columns:
        c.execute("ALTER TABLE submissions ADD COLUMN enrollment_no TEXT")
        
    conn.commit()
    conn.close()

def create_app():
    app = Flask(__name__)
    
    with open('config.json', 'r') as f:
        app_config = json.load(f)
        
    app.secret_key = os.urandom(16)
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['ACTIVE_LAB'] = app_config.get("active_lab", "default_lab")
    app.config['VALID_DEPTS'] = app_config.get("departments", [])
    
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=app_config.get("session_timeout_seconds", 1200))
    
    # Register Blueprints
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Initialize Directories & Database
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for dept in app.config['VALID_DEPTS']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], dept), exist_ok=True)
        
    init_db() # <--- Ensures table is ready on boot

    allowed_ips = ['127.0.0.1'] + ['192.168.31.'+str(i) for i in list(range(255))] + ['10.10.10.' + str(i) for i in [26, 13]+list(range(104, 144))]
    
    @app.before_request
    def limit_remote_addr():
        if request.remote_addr not in allowed_ips:
            abort(403)
            dx
    return app
