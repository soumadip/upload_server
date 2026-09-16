import subprocess
from flask import current_app

ALLOWED_EXTENSIONS = {'c', 'cpp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def code_has_error(fname):
    try:
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
        current_app.logger.info(f"Invalid roll no {inp}")
        return '00'
    elif int(inp) < 10:
        return '0' + str(int(inp))
    return str(int(inp))

def make_fname(basename, session_data):
    return '_'.join([session_data['roll_no'], session_data['enrollment_no'], session_data['id'], basename])

def process_fname(fname):
    return '_'.join(fname.split('_')[3:])
