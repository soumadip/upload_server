from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort, send_file
from werkzeug.utils import secure_filename
from datetime import timedelta
import os
import secrets
import time
import logging
import subprocess
import sqlite3
import zipfile
import io
import csv
import json 

# --- CONFIGURATION ---
ALLOWED_EXTENSIONS = {'c', 'cpp'}

# Load Configuration
with open('config.json', 'r') as config_file:
    app_config = json.load(config_file)

ACTIVE_LAB = app_config.get("active_lab", "default_lab")
ADMIN_PIN = app_config.get("admin_pin", "0000")
SESSION_TIMEOUT = app_config.get("session_timeout_seconds", 1200)
VALID_DEPTS = app_config.get("departments", [])

ACTIVE_LAB = "lab_test_01" # Change this for different exams (e.g., dsa_midterm, algo_lab_2)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_TIMEOUT)
app.config['ACTIVE_LAB'] = ACTIVE_LAB

allowed_ips = ['127.0.0.1'] + ['192.168.31.'+str(i) for i in list(range(255))] + ['10.10.10.' + str(i) for i in [26, 13]+list(range(104, 144))]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id TEXT, roll_no TEXT, dept TEXT, 
                  filename TEXT, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# --- UTILITIES ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def code_has_error(fname):
    try:
        # Added a 5-second timeout to prevent infinite loops from hanging the server
        res = subprocess.run(['gcc', '-lm', fname], capture_output=True, text=True, timeout=5)
        if "error:" in res.stderr:
            return True, "Compilation Error"
        elif "warning:" in res.stderr:
            return False, "Warning"
        return False, "Success"
    except subprocess.TimeoutExpired:
        return True, "Timeout"

def format_roll(inp):
    if len(inp) >= 3:
        out = '00'
        app.logger.info("format_roll:: invalid roll no %s", inp)
    elif int(inp) < 10:
        out = '0' + str(int(inp))
    else:
        out = str(int(inp))
    return out

def make_fname(basename, session):
    return '_'.join([session['roll_no'], session['enrollment_no'], session['id'], basename])

def process_fname(fname):
    tokens = fname.split('_')
    return '_'.join(tokens[3:])

# --- ROUTES ---
@app.before_request
def limit_remote_addr():
    if request.remote_addr not in allowed_ips:
        abort(403)

@app.route('/')
def home():
    return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        session.permanent = True
        # Using a short random hex instead of a file counter prevents race conditions
        session['id'] = '[' + secrets.token_hex(2) + ']'
        session['name'] = request.form['name'].strip()
        session['dept'] = request.form['dept']
        session['roll_no'] = format_roll(request.form['roll_no'])
        session['enrollment_no'] = request.form['enrollment_no']
        session['start_time'] = time.time()   
        session['end_time'] = session['start_time'] + SESSION_TIMEOUT

        flash("You are now logged in")
        app.logger.info('LOG IN ALERT [id %s]:: %s, ROLL: %s, Dept: %s', session['id'], session['name'], session['roll_no'], session['dept'].upper())
        return redirect(url_for('upload'))

    # Pass the departments list to the HTML template
    return render_template('setup.html', departments=VALID_DEPTS)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'enrollment_no' not in session or time.time() - session['start_time'] > SESSION_TIMEOUT:
        flash('Session expired! Please set up again.', 'danger')
        return redirect(url_for('setup'))

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                safe_filename = secure_filename(file.filename)
                mod_fname = make_fname(safe_filename, session)
                savefile = os.path.join(app.config['UPLOAD_FOLDER'], session['dept'], mod_fname)
                file.save(savefile)
                
                has_err, status = code_has_error(savefile)
                
                # Log to Database
                conn = sqlite3.connect('lab_sessions.db')
                c = conn.cursor()
                c.execute("INSERT INTO submissions (assignment_id, roll_no, dept, filename, status) VALUES (?, ?, ?, ?, ?)", 
                          (app.config['ACTIVE_LAB'], session['roll_no'], session['dept'], mod_fname, status))
                conn.commit()
                conn.close()

                if has_err:
                    app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s [ERROR/TIMEOUT]', session['roll_no'], safe_filename)
                    flash(f'{safe_filename} uploaded but failed compilation ({status}).', 'danger')
                else:
                    app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s', session['roll_no'], safe_filename)
                    flash(f'{safe_filename} uploaded successfully.', 'success')
            else:
                flash('Invalid file type. Only .c and .cpp allowed.', 'danger')

    # Fetch files for UI display
    dept_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['dept'])
    files = [f for f in os.listdir(dept_dir) if f.startswith(session['roll_no'] + '_' + session['enrollment_no'] + '_')]
    c_files = [process_fname(f) for f in files if session['id'] in f]
    p_files = [process_fname(f) for f in files if session['id'] not in f]
    
    return render_template('upload.html', curr_files=c_files, prev_files=p_files)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'enrollment_no' not in session:
        return redirect(url_for('setup'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], session['dept'], make_fname(filename, session))
    if os.path.isfile(filepath):
        os.remove(filepath)
        app.logger.info('DELETE ALERT:: ROLL: %s --> %s', session['roll_no'], filename)
        flash('File deleted successfully.', 'success')
    else:
        flash('File not found or access denied.', 'danger')

    return redirect(url_for('upload'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('setup'))

# --- ADMIN ROUTES ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        if request.form.get('pin') == ADMIN_PIN:
            session['is_admin'] = True
        else:
            flash('Invalid PIN', 'danger')
            
    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT id, roll_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ? ORDER BY timestamp DESC", (app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()
    
    return render_template('admin.html', logged_in=True, subs=subs, active_lab=app.config['ACTIVE_LAB'])

@app.route('/admin/download_zip')
def download_zip():
    if not session.get('is_admin'): abort(403)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for file in files:
                zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), app.config['UPLOAD_FOLDER']))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{app.config['ACTIVE_LAB']}_files.zip", as_attachment=True)

@app.route('/admin/export_csv')
def export_csv():
    if not session.get('is_admin'): abort(403)
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT roll_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ?", (app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll No', 'Department', 'Filename', 'Status', 'Timestamp'])
    writer.writerows(subs)
    return app.response_class(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={app.config['ACTIVE_LAB']}_report.csv"})

if __name__ == '__main__':
    init_db()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Dynamically create directories from config.json
    for subdir in VALID_DEPTS:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], subdir), exist_ok=True)

    logging.basicConfig(filename='app.log', level=logging.INFO)
    app.logger.info('\n\n_______START OF SESSION_______\n\n')
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
