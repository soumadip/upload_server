from flask import Flask, abort, request
from datetime import timedelta
import json, os, logging, sqlite3
from .blueprints.student import student_bp
from .blueprints.admin import admin_bp

def init_db():
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id TEXT, roll_no TEXT, enrollment_no TEXT, dept TEXT,
                  filename TEXT, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # Safe migration: Add missing columns dynamically
    c.execute("PRAGMA table_info(submissions)")
    columns = [column[1] for column in c.fetchall()]

    if 'enrollment_no' not in columns:
        c.execute("ALTER TABLE submissions ADD COLUMN enrollment_no TEXT")

    # NEW: Add a column to store the compiler/runtime logs
    if 'output_log' not in columns:
        c.execute("ALTER TABLE submissions ADD COLUMN output_log TEXT")

    conn.commit()
    conn.close()
    
def create_app():
    app = Flask(__name__)

    with open('config.json', 'r') as f:
        app_config = json.load(f)

    # 1. Use a persistent secret key
    app.secret_key = app_config.get("secret_key", os.urandom(16))

    # 2. Set upload size limits (e.g., 5 MB)
    app.config['MAX_CONTENT_LENGTH'] = app_config.get("max_upload_mb", 5) * 1024 * 1024

    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['ACTIVE_LAB'] = app_config.get("active_lab", "default_lab")
    app.config['VALID_DEPTS'] = app_config.get("departments", [])
    app.config['LAB_EXTENSIONS'] = app_config.get("lab_extensions", {})
    app.config['ADMIN_PIN'] = app_config.get("admin_pin", "0000")

    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=app_config.get("session_timeout_seconds", 1200))

    app.config['SUBMISSIONS_OPEN'] = app_config.get("submissions_open", True)

    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for dept in app.config['VALID_DEPTS']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], dept), exist_ok=True)

    init_db()

    # 3. Dynamic IP Allowlist using prefixes
    allowed_prefixes = app_config.get("allowed_ip_prefixes", ['127.0.0.1'])

    @app.before_request
    def limit_remote_addr():
        # Check if the incoming IP starts with any of our allowed prefixes
        if not any(request.remote_addr.startswith(prefix) for prefix in allowed_prefixes):
            abort(403)

    return app
