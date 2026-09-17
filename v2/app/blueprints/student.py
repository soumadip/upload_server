from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
import os, sqlite3, secrets, time
from werkzeug.utils import secure_filename
from ..utils import allowed_file, format_roll, make_fname, process_fname
from ..grader import evaluate_submission # <-- Import the secure sandboxed grader

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
def home():
    return redirect(url_for('student.setup'))

@student_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        session.permanent = True
        session['id'] = '[' + secrets.token_hex(2) + ']'
        session['name'] = request.form['name'].strip()
        session['dept'] = request.form['dept']
        session['roll_no'] = format_roll(request.form['roll_no'])
        session['enrollment_no'] = request.form['enrollment_no']
        session['start_time'] = time.time()   
        session['end_time'] = session['start_time'] + current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()

        flash("You are now logged in")
        current_app.logger.info('LOG IN ALERT [id %s]:: %s, ROLL: %s, Dept: %s', session['id'], session['name'], session['roll_no'], session['dept'].upper())
        return redirect(url_for('student.upload'))

    return render_template('setup.html', departments=current_app.config['VALID_DEPTS'])

@student_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    timeout_seconds = current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
    if 'enrollment_no' not in session or time.time() - session.get('start_time', 0) > timeout_seconds:
        flash('Session expired! Please set up again.', 'danger')
        return redirect(url_for('student.setup'))

    active_lab = current_app.config['ACTIVE_LAB']

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                safe_filename = secure_filename(file.filename)
                mod_fname = make_fname(safe_filename, session)
                save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], active_lab, session['dept'])
                os.makedirs(save_dir, exist_ok=True)

                savefile = os.path.join(save_dir, mod_fname)
                file.save(savefile)

                status = "Uploaded"
                conn = sqlite3.connect('lab_sessions.db')
                c = conn.cursor()
                c.execute("INSERT INTO submissions (assignment_id, roll_no, enrollment_no, dept, filename, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (active_lab, session['roll_no'], session['enrollment_no'], session['dept'], mod_fname, status))
                conn.commit()
                conn.close()

                if "Error" in status or "Failed" in status:
                    flash(f'{safe_filename} uploaded but failed: {status}', 'danger')
                else:
                    flash(f'{safe_filename} uploaded successfully.', 'success')
            else:
                flash('Invalid file type for this lab session.', 'danger')

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()

    # NEW: Automatically queue any previous session/historical files that are still 'Uploaded'
    # The LIKE check ensures we ignore the current active session ID
    c.execute("""
        UPDATE submissions 
        SET status = 'Pending Evaluation' 
        WHERE roll_no = ? AND enrollment_no = ? AND status = 'Uploaded'
        AND (assignment_id != ? OR filename NOT LIKE ?)
    """, (session['roll_no'], session['enrollment_no'], active_lab, f"%{session['id']}%"))
    conn.commit()

    # Fetch ALL files cleanly in one query
    c.execute("SELECT filename, status, timestamp, assignment_id FROM submissions WHERE roll_no = ? AND enrollment_no = ? ORDER BY timestamp DESC",
              (session['roll_no'], session['enrollment_no']))
    records = c.fetchall()
    conn.close()

    c_files = []
    p_files = []
    historical_files = []

    for r in records:
        file_info = {'original': process_fname(r[0]), 'full': r[0], 'status': r[1], 'time': r[2], 'lab': r[3]}
        # Sort into Current Lab vs Historical Labs
        if r[3] == active_lab:
            if session['id'] in r[0]:
                c_files.append(file_info)
            else:
                p_files.append(file_info)
        else:
            historical_files.append(file_info)

    allowed_exts = current_app.config['LAB_EXTENSIONS'].get(active_lab, ['c', 'cpp'])
    accept_string = ",".join([f".{ext}" for ext in allowed_exts])

    return render_template('upload.html', curr_files=c_files, prev_files=p_files, historical_files=historical_files, accept_string=accept_string)

@student_bp.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'enrollment_no' not in session:
        return redirect(url_for('student.setup'))

    #filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session['dept'], filename)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()

    # CRITICAL FIX 2: Ensure the student actually owns this file (IDOR prevention)
    c.execute("SELECT assignment_id, roll_no, enrollment_no FROM submissions WHERE filename = ?", (filename,))
    record = c.fetchone()

    if not record:
        conn.close()
        flash('File not found.', 'danger')
        return redirect(url_for('student.upload'))

    db_lab, db_roll, db_enroll = record

    # NEW: Construct the path using the db_lab
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], db_lab, session['dept'], filename)

    if db_roll != session['roll_no'] or db_enroll != session['enrollment_no']:
        conn.close()
        flash('Action forbidden: You cannot delete files belonging to other students.', 'danger')
        return redirect(url_for('student.upload'))

    if db_lab != current_app.config['ACTIVE_LAB']:
        conn.close()
        flash('Action forbidden: Cannot modify files from previous lab sessions.', 'danger')
        return redirect(url_for('student.upload'))

    # Safe to delete
    if os.path.isfile(filepath):
        os.remove(filepath)

    c.execute("DELETE FROM submissions WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()

    flash('File deleted successfully.', 'success')
    return redirect(url_for('student.upload'))

@student_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('student.setup'))

@student_bp.route('/request_eval/<filename>', methods=['POST'])
def request_eval(filename):
    if 'enrollment_no' not in session: return redirect(url_for('student.setup'))

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # Verify ownership before updating
    c.execute("SELECT id FROM submissions WHERE filename = ? AND roll_no = ? AND enrollment_no = ?",
              (filename, session['roll_no'], session['enrollment_no']))
    if c.fetchone():
        # Change status so the lazy grader picks it up
        c.execute("UPDATE submissions SET status = 'Pending Evaluation' WHERE filename = ?", (filename,))
        conn.commit()
        flash('Evaluation requested. Your code is now queued.', 'success')
    else:
        flash('Action forbidden.', 'danger')
    conn.close()
    return redirect(url_for('student.upload'))

@student_bp.route('/view_report/<filename>')
def view_report(filename):
    if 'enrollment_no' not in session: return "Unauthorized", 403

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # Fetch both the log AND the status
    c.execute("SELECT output_log, status FROM submissions WHERE filename = ? AND roll_no = ? AND enrollment_no = ?",
              (filename, session['roll_no'], session['enrollment_no']))
    record = c.fetchone()
    conn.close()

    if record:
        db_log, db_status = record

        if not db_log:
            return "Evaluation pending or no logs generated."

        # 1. If it's a compiler error, give them the full error log so they can debug
        if db_status in ['Compilation Error', 'Syntax Error']:
            return f"Status: {db_status}\n\n{db_log}"

        # 2. If it reached the test cases, hide the inputs/outputs to prevent cheating
        return (f"Final Evaluation Status: {db_status}\n\n"
                f"Compilation successful.\n"
                f"Detailed test case inputs and outputs are hidden to maintain academic integrity.")

    return "Report not found.", 404
