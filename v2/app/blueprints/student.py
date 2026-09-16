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
                    current_app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s [ERROR/TIMEOUT]', session['roll_no'], safe_filename)
                    flash(f'{safe_filename} uploaded but failed compilation ({status}).', 'danger')
                else:
                    current_app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s', session['roll_no'], safe_filename)
                    flash(f'{safe_filename} uploaded successfully.', 'success')
            else:
                flash('Invalid file type. Only .c and .cpp allowed.', 'danger')

    dept_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], session['dept'])
    if not os.path.exists(dept_dir):
        os.makedirs(dept_dir, exist_ok=True)

    files = [f for f in os.listdir(dept_dir) if f.startswith(str(session['roll_no']) + '_' + str(session['enrollment_no']) + '_')]
    c_files = [process_fname(f) for f in files if session['id'] in f]
    p_files = [process_fname(f) for f in files if session['id'] not in f]
    
    return render_template('upload.html', curr_files=c_files, prev_files=p_files)

@student_bp.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'enrollment_no' not in session:
        return redirect(url_for('student.setup'))

    target_fname = make_fname(filename, session)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], session['dept'], target_fname)
    
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT assignment_id FROM submissions WHERE filename = ?", (target_fname,))
    record = c.fetchone()
    conn.close()

    if record and record[0] != current_app.config['ACTIVE_LAB']:
        flash('Action forbidden: Cannot modify files from previous lab sessions.', 'danger')
        return redirect(url_for('student.upload'))

    if os.path.isfile(filepath):
        os.remove(filepath)
        flash('File deleted successfully.', 'success')
    else:
        flash('File not found.', 'danger')
        
    return redirect(url_for('student.upload'))

@student_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('student.setup'))
