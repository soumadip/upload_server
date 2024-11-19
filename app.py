from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from datetime import timedelta
import os
import secrets
import time
from threading import Thread, Lock
import threading
import logging
import subprocess

def code_has_warning(fname):
    res = subprocess.run(['gcc', '-lm', fname], capture_output=True, text=True)
    #print(res)
    if ("warning:" in res.stderr):
        return True

def code_has_error(fname):
    res = subprocess.run(['gcc', '-lm', fname], capture_output=True, text=True)
    print(res)
    if ("error:" in res.stderr):
        return True

allowed_ips = ['127.0.0.1'] + ['192.168.31.'+str(i) for i in list(range(255))] + ['10.10.10.' + str(i) for i in [26, 13]+list(range(104, 144))]
mutex = Lock()
SESSION_TIMEOUT = 1200
global COUNTER

app = Flask(__name__)


def is_session_valid():
    """Check if the session is still valid based on the set timeout."""
    return 'id' in session and (time.time() - session['start_time'] <= SESSION_TIMEOUT)

@app.before_request
def limit_remote_addr():
    if request.remote_addr in allowed_ips:
        print("allowed", request.remote_addr)
    else:
        print("not allowed", request.remote_addr)
        abort(403)

@app.route('/')
def home():
    return redirect(url_for('setup'))

def format_roll(inp):
	if len(inp)>=3:
		out = '00'
		app.logger.info("format_roll:: invalid roll no %s", inp)
	elif int(inp)<10:
		out = '0'+str(int(inp))
	else:
		out = str(int(inp))
	app.logger.debug("format_roll:: %s --> %s", inp, out)
	return out

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if 'id' not in session:
        return redirect(url_for('setup'))
    else:
        app.logger.info('LOG OUT ALERT [id %s]:: %s, ROLL: %s, Dept: %s', session['id'], session['name'], session['roll_no'], session['dept'].upper())
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global COUNTER
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['dept']
        roll_no = request.form['roll_no']
        enrollment_no = request.form['enrollment_no']
        #enrollment_no_confirm = request.form['enrollment_no_confirm']

        #if enrollment_no != enrollment_no_confirm:
        #    flash('Enrollment numbers do not match!', 'danger')
        #    return redirect(url_for('setup'))

        mutex.acquire()
        COUNTER += 1
        sess_id = str(COUNTER)
        mutex.release()

        session.permanent = True
        session['id'] = '[' + sess_id + ']'
        session['name'] = name.strip()
        session['dept'] = dept
        session['roll_no'] = format_roll(roll_no)
        session['enrollment_no'] = enrollment_no
        session['start_time'] = time.time()   
        session['end_time'] = session['start_time'] + SESSION_TIMEOUT

        flash("You are now logged in")
        app.logger.info('LOG IN ALERT [id %s]:: %s, ROLL: %s, Dept: %s', session['id'], session['name'], session['roll_no'], session['dept'].upper())
        return redirect(url_for('upload'))

    return render_template('setup.html')


def make_fname(basename, session):
	mod_fname = '_'.join([session['roll_no'], session['enrollment_no'], session['id'], basename])
	app.logger.debug("make_fname:: %s -->  mod: %s", basename, mod_fname)
	return mod_fname

def process_fname(fname):
    tokens = fname.split('_')
    app.logger.debug("process_fname:: %s --> ret:%s", fname, tokens[3:])
    return '_'.join(tokens[3:])
    
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'enrollment_no' not in session or time.time() - session['start_time'] > SESSION_TIMEOUT:
        flash('Session expired! Please set up again.', 'danger')
        return redirect(url_for('setup'))

    if request.method == 'POST':
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and file.filename:
                savefile = os.path.join(app.config['UPLOAD_FOLDER'], session['dept'], make_fname(file.filename, session))
                file.save(savefile)
                if(code_has_error(savefile)):
                    app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s [NOTE:COMPILATION ERROR DETECTED]', session['roll_no'], file.filename)
                    flash('File uploaded successfully [some file(s) contains compilation error].', 'success')
                elif(code_has_warning(savefile)):
                    app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s [NOTE:COMPILATION WARNING DETECTED]', session['roll_no'], file.filename)
                    flash('File uploaded successfully.', 'success')
                else:
                    app.logger.info('UPLOAD ALERT:: ROLL: %s --> %s', session['roll_no'], file.filename)
                    flash('File uploaded successfully.', 'success')

    files = [f for f in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'],session['dept'])) if f.startswith(session['roll_no'] + '_' + session['enrollment_no'] + '_')]
    c_files = [process_fname(f) for f in files if session['id'] in f]
    p_files = [process_fname(f) for f in files if session['id'] not in f]
    return render_template('upload.html', curr_files=c_files, prev_files=p_files)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if 'enrollment_no' not in session:
        return redirect(url_for('setup'))

    filepath = os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], session['dept'], make_fname(filename, session)))
    if os.path.isfile(filepath):
        os.remove(filepath)
        app.logger.info('DELETE ALERT:: ROLL: %s --> %s', session['roll_no'], filename)
        flash('File deleted successfully.', 'success')
    else:
        flash('File not found or access denied.', 'danger')

    return redirect(url_for('upload'))

@app.route('/files/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    
if __name__ == '__main__':
    debug_mode_on = True
    UPLOAD_FOLDER = 'uploads'

    app.secret_key = secrets.token_hex(16)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['SESSION_PERMANENT'] = True  # Enable permanent sessions
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_TIMEOUT)

	# Ensure the upload directory and subdirectories exiss
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for subdir in ['it', 'iot', 'iotcsbt']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], subdir), exist_ok=True)
	
	#setup log file
    if (debug_mode_on):
        file_handler = logging.FileHandler('app.debug.log')
    else:
        file_handler = logging.FileHandler('app.log')
    app.logger.addHandler(file_handler)

    if (debug_mode_on):
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)

    app.logger.info('\n\n_______START OF SESSION_______\n\n')

    global COUNTER
    with open("counter","r") as f:
        COUNTER = int(f.readline())
        print ('COUNTER START', COUNTER)

    if (debug_mode_on):
        app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=True)
    else:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    with open("counter","w") as f:
        print('COUNTER SAVED', COUNTER)
        f.write('{}'.format(COUNTER))

    print('Server shutting down...')
	
	
