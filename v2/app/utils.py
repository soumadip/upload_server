import subprocess, os
from flask import current_app

# Expanded allowed extensions
ALLOWED_EXTENSIONS = {'c', 'cpp', 'java', 'py', 'sh'}

def get_allowed_extensions():
    # Fetch the extensions for the current lab, default to ['c', 'cpp'] if missing
    active = current_app.config['ACTIVE_LAB']
    return current_app.config['LAB_EXTENSIONS'].get(active, ['c', 'cpp'])

def allowed_file(filename):
    allowed = get_allowed_extensions()
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def run_test_cases(executable_path, lang="c"):
    # Placeholder for future test case execution logic
    return "Success"

def run_test_cases(executable_path):
    # FUTURE SCAFFOLDING:
    # Here is where you will use subprocess to push inputs to the compiled binary
    # and compare the stdout to your expected outputs for algorithm design tasks.
    # Example:
    # try:
    #     res = subprocess.run([executable_path], input="5\n", text=True, capture_output=True, timeout=2)
    #     if res.stdout.strip() == "120": return "Passed 1/1"
    # except subprocess.TimeoutExpired: return "Time Limit Exceeded (TLE)"

    return "Success"

def code_has_error(fname):
    ext = fname.rsplit('.', 1)[1].lower()
    
    try:
        # --- C ---
        if ext == 'c':
            executable = fname + ".out"
            res = subprocess.run(['gcc', '-lm', '-pthread', fname, '-o', executable], capture_output=True, text=True, timeout=5)
            if res.returncode != 0 or "error:" in res.stderr.lower():
                return True, "Compilation Error"
            
            status = run_test_cases(executable, "c")
            if os.path.exists(executable): os.remove(executable) # Cleanup
            if "warning:" in res.stderr.lower(): return False, f"{status} (with warnings)"
            return False, status

        # --- C++ ---
        elif ext == 'cpp':
            executable = fname + ".out"
            res = subprocess.run(['g++', '-lm', '-pthread', fname, '-o', executable], capture_output=True, text=True, timeout=5)
            if res.returncode != 0 or "error:" in res.stderr.lower():
                return True, "Compilation Error"
            
            status = run_test_cases(executable, "cpp")
            if os.path.exists(executable): os.remove(executable) # Cleanup
            if "warning:" in res.stderr.lower(): return False, f"{status} (with warnings)"
            return False, status

        # --- JAVA ---
        elif ext == 'java':
            res = subprocess.run(['javac', fname], capture_output=True, text=True, timeout=5)
            if res.returncode != 0 or "error:" in res.stderr.lower():
                return True, "Compilation Error"
            
            # Java creates a .class file with the same base name, we need to clean it up
            class_file = fname.rsplit('.', 1)[0] + ".class"
            if os.path.exists(class_file): os.remove(class_file)
            return False, "Success (Compiled)"

        # --- PYTHON ---
        elif ext == 'py':
            # Perform a strict syntax check without running the code
            res = subprocess.run(['python3', '-m', 'py_compile', fname], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return True, "Syntax Error"
            return False, "Success (Syntax Checked)"

        # --- BASH / SHELL ---
        elif ext == 'sh':
            # -n flag reads commands but does not execute them (syntax check)
            res = subprocess.run(['bash', '-n', fname], capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                return True, "Syntax Error"
            return False, "Success (Syntax Checked)"

        else:
            return False, "Success (Unchecked Format)"
            
    except subprocess.TimeoutExpired:
        return True, "Timeout during Check/Compilation"

def format_roll(inp):
    if len(inp) >= 3: return '00'
    elif int(inp) < 10: return '0' + str(int(inp))
    return str(int(inp))

def make_fname(basename, session_data):
    return '_'.join([session_data['roll_no'], session_data['enrollment_no'], session_data['id'], basename])

def process_fname(fname):
    return '_'.join(fname.split('_')[3:])
