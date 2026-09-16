from flask import current_app

def get_allowed_extensions():
    active = current_app.config['ACTIVE_LAB']
    return current_app.config['LAB_EXTENSIONS'].get(active, ['c', 'cpp'])

def allowed_file(filename):
    allowed = get_allowed_extensions()
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def format_roll(inp):
    # HIGH PRIORITY FIX 5: Prevent crash on non-numeric and fix truncation bug
    try:
        val = int(inp)
        if val < 10: return f"0{val}"
        return str(val)
    except ValueError:
        return str(inp)[:3] # Fallback for alphanumeric rolls

def make_fname(basename, session_data):
    return '_'.join([session_data['roll_no'], session_data['enrollment_no'], session_data['id'], basename])

def process_fname(fname):
    return '_'.join(fname.split('_')[3:])
