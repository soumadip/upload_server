from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
import os, sqlite3, secrets, time
from werkzeug.utils import secure_filename
from ..utils import allowed_file, code_has_error, format_roll, make_fname, process_fname

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

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                safe_filename = secure_filename(file.filename)
                mod_fname = make_fname(safe_filename, session)
                savefile = os.path.join(current_app.config['UPLOAD_FOLDER'], session['dept'], mod_fname)
                file.save(savefile)

                has_err, status = code_has_error(savefile)

                conn = sqlite3.connect('lab_sessions.db')
                c = conn.cursor()
                c.execute("INSERT INTO submissions (assignment_id, roll_no, enrollment_no, dept, filename, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (current_app.config['ACTIVE_LAB'], session['roll_no'], session['enrollment_no'], session['dept'], mod_fname, status))
                conn.commit()
                conn.close()

                if has_err:
                    flash(f'{safe_filename} uploaded but failed: {status}', 'danger')
                else:
                    flash(f'{safe_filename} uploaded successfully.', 'success')
            else:
                flash('Invalid file type. Only .c and .cpp allowed.', 'danger')

    # Fetch files AND their status from the database instead of the OS folder
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT filename, status, timestamp FROM submissions WHERE roll_no = ? AND enrollment_no = ? AND assignment_id = ? ORDER BY timestamp DESC",
              (session['roll_no'], session['enrollment_no'], current_app.config['ACTIVE_LAB']))
    records = c.fetchall()
    conn.close()

    # Split into current session vs previous based on the session ID token
    c_files = [{'original': process_fname(r[0]), 'full': r[0], 'status': r[1], 'time': r[2]} for r in records if session['id'] in r[0]]
    p_files = [{'original': process_fname(r[0]), 'full': r[0], 'status': r[1], 'time': r[2]} for r in records if session['id'] not in r[0]]

    # Generate the string for the HTML accept attribute (e.g., ".c,.cpp")
    active_lab = current_app.config['ACTIVE_LAB']
    allowed_exts = current_app.config['LAB_EXTENSIONS'].get(active_lab, ['c', 'cpp'])
    accept_string = ",".join([f".{ext}" for ext in allowed_exts])
    
    return render_template('upload.html', curr_files=c_files, prev_files=p_files, accept_string=accept_string)

@student_bp.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'enrollment_no' not in session:
        return redirect(url_for('student.setup'))

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session['dept'], filename)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT assignment_id FROM submissions WHERE filename = ?", (filename,))
    record = c.fetchone()

    if record and record[0] != current_app.config['ACTIVE_LAB']:
        conn.close()
        flash('Action forbidden: Cannot modify files from previous lab sessions.', 'danger')
        return redirect(url_for('student.upload'))

    # Delete from physical storage
    if os.path.isfile(filepath):
        os.remove(filepath)

    # Delete from database so it vanishes from the UI
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
