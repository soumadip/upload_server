import sqlite3
import os
import subprocess
import time

def evaluate_submission(filepath, filename):
    """
    Spins up the Docker sandbox to compile and check the code.
    Uses strict memory limits, drops all network access, and prevents fork-bombs.
    """
    ext = filename.rsplit('.', 1)[1].lower()
    host_dir = os.path.abspath(os.path.dirname(filepath))
    
    # Mount the specific department folder as read-only, but mount a tmpfs for compilation outputs
    docker_base_cmd = [
        "docker", "run", "--rm",
        "--network", "none",               # Block internet access
        "--memory", "128m",                # Prevent memory leaks
        "--pids-limit", "50",              # Prevent fork-bombs
        "-v", f"{host_dir}:/sandbox:ro",   # Read-only access to student files
        "--tmpfs", "/tmp:exec",            # Ramdisk for compiled binaries
        "lab_sandbox", "bash", "-c"
    ]
    
    try:
        if ext == 'c':
            # Compile to the tmpfs ramdisk, then run
            compile_cmd = f"gcc -lm -pthread /sandbox/{filename} -o /tmp/out"
            run_cmd = "/tmp/out" # We will pipe test cases into this later
            
            res = subprocess.run(
                docker_base_cmd + [f"{compile_cmd} && {run_cmd}"], 
                capture_output=True, text=True, timeout=5
            )
            
            if res.returncode != 0:
                return "Compilation/Runtime Error"
            return "Success"
            
        elif ext == 'py':
            res = subprocess.run(
                docker_base_cmd + [f"python3 -m py_compile /sandbox/{filename}"], 
                capture_output=True, text=True, timeout=5
            )
            if res.returncode != 0:
                return "Syntax Error"
            return "Success"
            
    except subprocess.TimeoutExpired:
        return "Timeout (Exceeded 5s limit)"
        
    return "Unchecked Format"

def run_grader():
    print("Starting lazy evaluation process...")
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    
    # Find all submissions waiting to be graded
    c.execute("SELECT id, dept, filename FROM submissions WHERE status = 'Pending Evaluation'")
    pending = c.fetchall()
    
    for sub_id, dept, filename in pending:
        print(f"Grading {filename}...")
        filepath = os.path.join('uploads', dept, filename)
        
        if not os.path.exists(filepath):
            new_status = "File Missing"
        else:
            new_status = evaluate_submission(filepath, filename)
            
        # Update database with the result
        c.execute("UPDATE submissions SET status = ? WHERE id = ?", (new_status, sub_id))
        conn.commit()
        print(f"Result: {new_status}")
        
    conn.close()
    print("Batch evaluation complete!")

if __name__ == "__main__":
    run_grader()
