import re
from flask import current_app

def get_allowed_extensions():
    active = current_app.config['ACTIVE_LAB']
    return current_app.config['LAB_EXTENSIONS'].get(active, ['c', 'cpp'])

def allowed_file(filename):
    allowed = get_allowed_extensions()
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def format_roll(inp):
    # Prevent crash on non-numeric input, fix the truncation-collision bug,
    # and strip to alphanumeric only so this can't carry shell metacharacters
    # into filenames the way the old unsanitized fallback could.
    try:
        val = int(inp)
        if val < 10: return f"0{val}"
        return str(val)
    except ValueError:
        cleaned = re.sub(r'[^A-Za-z0-9]', '', str(inp))
        return cleaned[:3] if cleaned else "000"

def make_fname(basename, session_data):
    return '_'.join([session_data['roll_no'], session_data['enrollment_no'], session_data['id'], basename])

def process_fname(fname):
    return '_'.join(fname.split('_')[3:])
