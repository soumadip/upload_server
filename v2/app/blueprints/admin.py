import hmac
from flask import Blueprint, render_template, request, session, flash, current_app, abort, send_file, send_from_directory, Response, redirect, url_for, jsonify
import sqlite3, os, zipfile, io, csv, json
import json
import threading
from flask import current_app
from ..grader import run_grader_task
from ..config_manager import create_new_lab, set_active_lab
import os

admin_bp = Blueprint('admin', __name__)

def get_admin_pin():
    with open('config.json', 'r') as f:
        return json.load(f).get("admin_pin", "0000")

@admin_bp.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        submitted_pin = request.form.get('pin', '')
        actual_pin = current_app.config.get('ADMIN_PIN', '')
        
        # Use constant-time comparison for security
        if hmac.compare_digest(submitted_pin, actual_pin):
            session['is_admin'] = True
        else:
            flash('Invalid PIN', 'danger')

    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # Upgraded query to also fetch enrollment_no (ensure your DB column matches, or if roll_no is combined)
    # Note: If enrollment number isn't explicitly saved as a column, we can fetch it or include it.
    # Let's add 'enrollment_no' to the query. If your table doesn't have it yet, see note below!
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
            # Using absolute path perfectly bypasses Flask's directory restrictions
            return send_file(os.path.abspath(filepath), as_attachment=True, download_name=filename)

    flash('File not found.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/download_zip')
def download_zip():
    if not session.get('is_admin'): abort(403)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(current_app.config['UPLOAD_FOLDER']):
            for file in files:
                zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), current_app.config['UPLOAD_FOLDER']))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{current_app.config['ACTIVE_LAB']}_files.zip", as_attachment=True)

@admin_bp.route('/export_csv')
def export_csv():
    if not session.get('is_admin'): abort(403)
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT roll_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ?", (current_app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll No', 'Department', 'Filename', 'Status', 'Timestamp'])
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

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
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
    if data.get('lab_name'):
        create_new_lab(current_app, data['lab_name'], data.get('extensions', ['c', 'cpp']))
        return jsonify({'status': 'success', 'message': f"Lab {data['lab_name']} initialized."})
    return jsonify({'error': 'Invalid data'}), 400

@admin_bp.route('/api/add_test_case_manual', methods=['POST'])
def api_add_test_case_manual():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    lab_name = request.json.get('lab_name')
    test_dir = os.path.join('test_cases', lab_name)
    os.makedirs(test_dir, exist_ok=True) # Ensure dir exists

    # Auto-increment the test case number
    existing = [f for f in os.listdir(test_dir) if f.startswith('input_')]
    next_num = len(existing) + 1

    with open(os.path.join(test_dir, f'input_{next_num}.txt'), 'w') as f: f.write(request.json.get('input_data', ''))
    with open(os.path.join(test_dir, f'output_{next_num}.txt'), 'w') as f: f.write(request.json.get('output_data', ''))

    return jsonify({'status': 'success', 'message': f'Saved as Test Case {next_num}'})

@admin_bp.route('/api/upload_test_cases', methods=['POST'])
def api_upload_test_cases():
    if not session.get('is_admin'): return jsonify({'error': 'Unauthorized'}), 403
    lab_name = request.form.get('lab_name')
    test_dir = os.path.join('test_cases', lab_name)
    os.makedirs(test_dir, exist_ok=True)

    count = 0
    for file in request.files.getlist('files'):
        if file and file.filename.endswith('.txt'):
            safe_name = secure_filename(file.filename) # Ensures it saves as input_1.txt safely
            file.save(os.path.join(test_dir, safe_name))
            count += 1

    return jsonify({'status': 'success', 'message': f'Uploaded {count} files to {lab_name}'})

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
    lab_name = request.json.get('lab_name')
    if lab_name in current_app.config.get('LAB_EXTENSIONS', {}):
        set_active_lab(current_app, lab_name)
        return jsonify({'status': 'success', 'message': f'Active lab changed to {lab_name}'})
    return jsonify({'error': 'Invalid lab name'}), 400
