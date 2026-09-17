import hmac
from flask import Blueprint, render_template, request, session, flash, current_app, abort, send_file, Response, redirect, url_for, jsonify
import sqlite3, os, zipfile, io, csv, threading, time
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from ..grader import run_grader_task
from ..config_manager import create_new_lab, set_active_lab

admin_bp = Blueprint('admin', __name__)

# --- RATE LIMITER DICTIONARY ---
FAILED_LOGINS = {}
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = 300 # 5 minutes

@admin_bp.route('/', methods=['GET', 'POST'])
def dashboard():
    ip = request.remote_addr
    now = time.time()

    # Clean expired lockouts
    if ip in FAILED_LOGINS and now > FAILED_LOGINS[ip]['lockout_until']:
        FAILED_LOGINS.pop(ip)

    if request.method == 'POST':
        # Enforce Lockout
        if ip in FAILED_LOGINS and FAILED_LOGINS[ip]['count'] >= MAX_ATTEMPTS:
            flash('Too many failed attempts. Try again in 5 minutes.', 'danger')
            return render_template('admin.html', logged_in=False)

        submitted_pin = request.form.get('pin', '')
        actual_pin = str(current_app.config.get('ADMIN_PIN', ''))
        
        if hmac.compare_digest(submitted_pin, actual_pin):
            session['is_admin'] = True
            if ip in FAILED_LOGINS:
                FAILED_LOGINS.pop(ip)
        else:
            attempts = FAILED_LOGINS.get(ip, {'count': 0, 'lockout_until': 0})
            attempts['count'] += 1
            if attempts['count'] >= MAX_ATTEMPTS:
                attempts['lockout_until'] = now + LOCKOUT_WINDOW
            FAILED_LOGINS[ip] = attempts
            flash('Invalid PIN', 'danger')

    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT id, roll_no, enrollment_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ? ORDER BY timestamp DESC", (current_app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    return render_template('admin.html', logged_in=True, subs=subs, active_lab=current_app.config['ACTIVE_LAB'])
    

@admin_bp.route('/download_single/<int:sub_id>')
def download_single(sub_id):
    if not session.get('is_admin'): return redirect(url_for('admin.dashboard'))

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT assignment_id, dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()
    conn.close()

    if record:
        db_lab, dept, filename = record

        # 1. Try the new nested path first
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], db_lab, dept, filename)

        # 2. Fallback to the legacy path
        if not os.path.exists(filepath):
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)

        if os.path.exists(filepath):
            # Using absolute path directly accesses the validated internal storage path
            return send_file(os.path.abspath(filepath), as_attachment=True, download_name=filename)

    flash('File not found.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/download_zip')
def download_zip():
    if not session.get('is_admin'): abort(403)

    active_lab = current_app.config['ACTIVE_LAB']

    # 1. Fetch only submissions for the active lab
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT roll_no, dept, filename FROM submissions WHERE assignment_id = ?", (active_lab,))
    records = c.fetchall()
    conn.close()

    memory_file = io.BytesIO()

    # 2. Build the ZIP file in memory
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for roll_no, dept, filename in records:
            # The physical location on the server's hard drive
            physical_path = os.path.join(current_app.config['UPLOAD_FOLDER'], active_lab, dept, filename)

            if os.path.exists(physical_path):
                # The clean, organized folder structure INSIDE the ZIP file
                zip_path = os.path.join(dept, roll_no, filename)
                zf.write(physical_path, zip_path)

    memory_file.seek(0)

    # 3. Send the neatly organized archive to the teacher
    return send_file(memory_file, download_name=f"{active_lab}_submissions.zip", as_attachment=True)

@admin_bp.route('/export_csv')
def export_csv():
    if not session.get('is_admin'): abort(403)
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # NEW: Added enrollment_no to the query
    c.execute("SELECT roll_no, enrollment_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ?", (current_app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    # NEW: Added Enrollment No to the header row
    writer.writerow(['Roll No', 'Enrollment No', 'Department', 'Filename', 'Status', 'Timestamp'])
    writer.writerows(subs)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={current_app.config['ACTIVE_LAB']}_report.csv"})

@admin_bp.route('/view/<int:sub_id>')
def view_file(sub_id):
    if not session.get('is_admin'): return "Unauthorized", 403

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT assignment_id, dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()
    conn.close()

    if not record: return "Not found", 404

    db_lab, dept, filename = record

    # 1. Try the new nested path first
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], db_lab, dept, filename)

    # 2. Fallback to the legacy path
    if not os.path.exists(filepath):
        # Using absolute path directly accesses the validated internal storage path
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            # We return plain text directly so JavaScript doesn't say [object Object]
            return f.read()

    return "File missing on server", 404

@admin_bp.route('/delete_sub/<int:sub_id>', methods=['POST'])
def delete_submission(sub_id):
    if not session.get('is_admin'): abort(403)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT assignment_id, dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()

    if record:
        db_lab, dept, filename = record

        # 1. Try the new nested path first
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], db_lab, dept, filename)

        # 2. Fallback to the legacy path
        if not os.path.exists(filepath):
            # Using absolute path directly accesses the validated internal storage path
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)

        # 3. Delete the physical file
        if os.path.exists(filepath):
            os.remove(filepath)

        # 4. Delete the database record
        c.execute("DELETE FROM submissions WHERE id = ?", (sub_id,))
        conn.commit()
        flash('File and record deleted successfully.', 'success')

    conn.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/submissions')
def api_submissions():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    conn = sqlite3.connect('lab_sessions.db', timeout=10)
    c = conn.cursor()

    # FIXED: Use exact UTC time so it perfectly aligns with SQLite's internal clock
    cutoff_time = (datetime.utcnow() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')

    try:
        c.execute("""
            UPDATE submissions
            SET status = 'Pending Evaluation'
            WHERE status = 'Uploaded'
            AND timestamp <= ?
        """, (cutoff_time,))
        conn.commit()
    except sqlite3.OperationalError:
        pass

    c.execute("SELECT id, roll_no, enrollment_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ? ORDER BY timestamp DESC", (current_app.config['ACTIVE_LAB'],))
    rows = c.fetchall()
    conn.close()

    # Format data into a list of dictionaries for DataTables
    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'roll_no': row[1],
            'enrollment_no': row[2],
            'dept': row[3],
            'filename': row[4],
            'status': row[5],
            'timestamp': row[6]
        })
    return jsonify(data)

@admin_bp.route('/trigger_grader', methods=['POST'])
def trigger_grader():
    if not session.get('is_admin'): abort(403)

    # Grab the actual Flask app instance to pass into the thread
    app = current_app._get_current_object()

    # Spawn the background grader task
    thread = threading.Thread(target=run_grader_task, args=(app,))
    thread.daemon = True
    thread.start()

    flash('Auto-grader started in the background. Submissions will update shortly as they are evaluated.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/grade_single/<int:sub_id>', methods=['POST'])
def grade_single(sub_id):
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    custom_input = request.json.get('custom_input', None)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()

    # NEW: Fetch assignment_id
    c.execute("SELECT assignment_id, dept, filename, output_log, status FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()

    if not record:
        conn.close()
        return jsonify({'error': 'Not found'}), 404

    db_lab, dept, filename, db_log, db_status = record

    if custom_input is None:
        conn.close()
        return jsonify({'status': db_status, 'log': db_log or 'No logs available. Run evaluation first.'})

    # NEW: Construct path using db_lab
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], db_lab, dept, filename)

    from ..grader import evaluate_submission
    status, log = evaluate_submission(filepath, filename, db_lab, custom_input)

    conn.close()
    return jsonify({'status': status, 'log': log})

@admin_bp.route('/api/create_lab', methods=['POST'])
def api_create_lab():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    safe_lab = secure_filename(data.get('lab_name', ''))
    if safe_lab:
        create_new_lab(current_app, safe_lab, data.get('extensions', ['c', 'cpp']))
        return jsonify({'status': 'success', 'message': f"Lab {safe_lab} initialized."})
    return jsonify({'error': 'Invalid data'}), 400

@admin_bp.route('/api/add_test_case_manual', methods=['POST'])
def api_add_test_case_manual():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    safe_lab = secure_filename(request.json.get('lab_name', ''))
    test_dir = os.path.join('test_cases', safe_lab)
    os.makedirs(test_dir, exist_ok=True)

    # Auto-increment the test case number
    existing = [f for f in os.listdir(test_dir) if f.startswith('input_')]
    next_num = len(existing) + 1

    with open(os.path.join(test_dir, f'input_{next_num}.txt'), 'w') as f: f.write(request.json.get('input_data', ''))
    with open(os.path.join(test_dir, f'output_{next_num}.txt'), 'w') as f: f.write(request.json.get('output_data', ''))

    return jsonify({'status': 'success', 'message': f'Saved as Test Case {next_num}'})

@admin_bp.route('/api/upload_test_cases', methods=['POST'])
def api_upload_test_cases():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    safe_lab = secure_filename(request.form.get('lab_name', ''))
    test_dir = os.path.join('test_cases', safe_lab)
    os.makedirs(test_dir, exist_ok=True)

    count = 0
    for file in request.files.getlist('files'):
        if file and file.filename.endswith('.txt'):
            safe_name = secure_filename(file.filename) # Ensures it saves as input_1.txt safely
            file.save(os.path.join(test_dir, safe_name))
            count += 1

    return jsonify({'status': 'success', 'message': f'Uploaded {count} files to {safe_lab}'})

@admin_bp.route('/api/get_labs', methods=['GET'])
def api_get_labs():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({
        'active_lab': current_app.config.get('ACTIVE_LAB'),
        'labs': list(current_app.config.get('LAB_EXTENSIONS', {}).keys())
    })

@admin_bp.route('/api/set_active_lab', methods=['POST'])
def api_set_active_lab():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    safe_lab = secure_filename(request.json.get('lab_name', ''))
    if safe_lab in current_app.config.get('LAB_EXTENSIONS', {}):
        set_active_lab(current_app, safe_lab)
        return jsonify({'status': 'success', 'message': f'Active lab changed to {safe_lab}'})
    return jsonify({'error': 'Invalid lab name'}), 400
