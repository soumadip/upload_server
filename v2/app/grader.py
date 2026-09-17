import sqlite3
import os
import subprocess

def evaluate_submission(filepath, filename, active_lab, custom_input=None):
    ext = filename.rsplit('.', 1)[1].lower()
    host_dir = os.path.abspath(os.path.dirname(filepath))
    test_dir = os.path.abspath(os.path.join('test_cases', active_lab))

    docker_base_cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "none", "--memory", "128m", "--pids-limit", "50",
        "-v", f"{host_dir}:/sandbox:ro", "lab_sandbox"
    ]

    input_files = []
    if os.path.exists(test_dir):
        input_files = sorted([f for f in os.listdir(test_dir) if f.startswith('input_')])

    # Recover the original filename to appease Java's strict class naming rules
    original_name = filename.split('_', 3)[-1] if '_' in filename else filename

    # 1. Define Language-Specific Commands
    if ext == 'c':
        compile_cmd = f"gcc -lm -pthread /sandbox/{filename} -o /tmp/out"
        run_cmd = "/tmp/out"
    elif ext == 'cpp':
        compile_cmd = f"g++ -lm -pthread /sandbox/{filename} -o /tmp/out"
        run_cmd = "/tmp/out"
    elif ext == 'py':
        compile_cmd = f"python3 -m py_compile /sandbox/{filename}"
        run_cmd = f"python3 /sandbox/{filename}"
    elif ext == 'sh':
        compile_cmd = f"bash -n /sandbox/{filename}"
        run_cmd = f"bash /sandbox/{filename}"
    elif ext == 'java':
        classname = original_name.rsplit('.', 1)[0]
        # Copy to /tmp to restore original filename, compile it, and run it
        compile_cmd = f"cp /sandbox/{filename} /tmp/{original_name} && javac /tmp/{original_name}"
        run_cmd = f"cd /tmp && java {classname}"
    else:
        return "Unchecked Format", f"Format .{ext} not supported for execution."

    # Chain them together so the runtime environment is perfect
    chained_cmd = f"{compile_cmd} && {run_cmd}"

    try:
        # 2. Syntax / Compilation Check
        comp_res = subprocess.run(docker_base_cmd + ["bash", "-c", compile_cmd], capture_output=True, text=True, timeout=5)
        if comp_res.returncode != 0:
            err_type = "Syntax Error" if ext in ['py', 'sh'] else "Compilation Error"
            return err_type, f"--- ERRORS ---\n{comp_res.stderr.strip()}"

        # 3. Custom Input Override (Admin Dashboard)
        if custom_input is not None:
            run_res = subprocess.run(docker_base_cmd + ["bash", "-c", chained_cmd], input=custom_input, text=True, capture_output=True, timeout=3)
            log = f"--- STDERR ---\n{run_res.stderr.strip()}\n--- STDOUT ---\n{run_res.stdout.strip()}"
            return "Success" if run_res.returncode == 0 else "Runtime Error", log

        # 4. Automated Test Cases
        if not input_files:
            return "Success", "Syntax/Compilation OK. No test cases provided."

        passed = 0
        total = len(input_files)
        full_log = ""

        for in_file in input_files:
            test_num = in_file.split('_')[1].split('.')[0]
            with open(os.path.join(test_dir, in_file), 'r') as f: test_input = f.read()
            with open(os.path.join(test_dir, f"output_{test_num}.txt"), 'r') as f: expected = f.read().strip().replace('\r', '')

            res = subprocess.run(docker_base_cmd + ["bash", "-c", chained_cmd], input=test_input, text=True, capture_output=True, timeout=3)

            if res.returncode != 0:
                full_log += f"--- Test {test_num} Runtime Error ---\n{res.stderr.strip()}\n\n"
                continue  # Skip to the next test case instead of halting

            student_output = res.stdout.strip().replace('\r', '')
            if student_output != expected:
                full_log += f"--- Test {test_num} Failed ---\nINPUT:\n{test_input}\n\nEXPECTED:\n{expected}\n\nGOT:\n{student_output}\n\n"
                continue  # Skip to the next test case instead of halting

            full_log += f"--- Test {test_num} Passed ---\n\n"
            passed += 1

        # Final Status Calculation
        if passed == total:
            return f"Passed {passed}/{total}", full_log
        else:
            return f"Failed ({passed}/{total})", full_log

    except subprocess.TimeoutExpired:
        return "Time Limit Exceeded", "Process killed. Infinite loop or timeout detected."

def run_grader_task(app):
    print("\n[GRADER] ⚙️ Auto-grader background thread started!")
    with app.app_context():
        conn = sqlite3.connect('lab_sessions.db')
        c = conn.cursor()

        # NEW: Fetch assignment_id as well
        c.execute("SELECT id, assignment_id, dept, filename FROM submissions WHERE status = 'Pending Evaluation'")
        pending = c.fetchall()

        print(f"[GRADER] Found {len(pending)} submissions pending evaluation.")

        for sub_id, assignment_id, dept, filename in pending:
            print(f"[GRADER] 👉 Compiling/Running: {filename}...")

            # NEW: Insert assignment_id into the path
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], assignment_id, dept, filename)

            if not os.path.exists(filepath):
                status, log = "File Missing", "System could not locate the file."
            else:
                status, log = evaluate_submission(filepath, filename, assignment_id)

            c.execute("UPDATE submissions SET status = ?, output_log = ? WHERE id = ?", (status, log, sub_id))
            conn.commit()
            print(f"[GRADER] ✅ Result for {filename}: {status}")

        conn.close()
        print("[GRADER] 🎉 Batch evaluation complete!\n")
