from flask import Blueprint, render_template, request, session, flash, current_app, abort, send_file, Response, redirect, url_for, jsonify
import sqlite3, os, zipfile, io, csv, json
import json

admin_bp = Blueprint('admin', __name__)

def get_admin_pin():
    with open('config.json', 'r') as f:
        return json.load(f).get("admin_pin", "0000")

@admin_bp.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        if request.form.get('pin') == get_admin_pin():
            session['is_admin'] = True
        else:
            flash('Invalid PIN', 'danger')

    if not session.get('is_admin'):
        return render_template('admin.html', logged_in=False)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    # Upgraded query to also fetch enrollment_no (ensure your DB column matches, or if roll_no is combined)
    # Note: If enrollment number isn't explicitly saved as a column, we can fetch it or include it.
    # Let's add 'enrollment_no' to the query. If your table doesn't have it yet, see note below!
    c.execute("SELECT id, roll_no, enrollment_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ? ORDER BY timestamp DESC", (current_app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    return render_template('admin.html', logged_in=True, subs=subs, active_lab=current_app.config['ACTIVE_LAB'])

@admin_bp.route('/download_single/<int:sub_id>')
def download_single(sub_id):
    if not session.get('is_admin'): abort(403)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()
    conn.close()

    if record:
        dept, filename = record
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)

    flash('File not found.', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/download_zip')
def download_zip():
    if not session.get('is_admin'): abort(403)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(current_app.config['UPLOAD_FOLDER']):
            for file in files:
                zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), current_app.config['UPLOAD_FOLDER']))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{current_app.config['ACTIVE_LAB']}_files.zip", as_attachment=True)

@admin_bp.route('/export_csv')
def export_csv():
    if not session.get('is_admin'): abort(403)
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT roll_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ?", (current_app.config['ACTIVE_LAB'],))
    subs = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll No', 'Department', 'Filename', 'Status', 'Timestamp'])
    writer.writerows(subs)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={current_app.config['ACTIVE_LAB']}_report.csv"})


@admin_bp.route('/view/<int:sub_id>')
def view_file(sub_id):
    if not session.get('is_admin'): abort(403)

    # Look up the exact file path from the database securely
    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()
    conn.close()

    if record:
        dept, filename = record
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            # Send as raw text so it renders right in the browser tab
            return Response(content, mimetype='text/plain')

    return abort(404)

@admin_bp.route('/delete_sub/<int:sub_id>', methods=['POST'])
def delete_submission(sub_id):
    if not session.get('is_admin'): abort(403)

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT dept, filename FROM submissions WHERE id = ?", (sub_id,))
    record = c.fetchone()

    if record:
        dept, filename = record
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], dept, filename)

        # 1. Delete the physical file
        if os.path.exists(filepath):
            os.remove(filepath)

        # 2. Delete the database record
        c.execute("DELETE FROM submissions WHERE id = ?", (sub_id,))
        conn.commit()
        flash('File and record deleted successfully.', 'success')

    conn.close()
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/submissions')
def api_submissions():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    conn = sqlite3.connect('lab_sessions.db')
    c = conn.cursor()
    c.execute("SELECT id, roll_no, enrollment_no, dept, filename, status, timestamp FROM submissions WHERE assignment_id = ? ORDER BY timestamp DESC", (current_app.config['ACTIVE_LAB'],))
    rows = c.fetchall()
    conn.close()

    # Format data into a list of dictionaries for DataTables
    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'roll_no': row[1],
            'enrollment_no': row[2],
            'dept': row[3],
            'filename': row[4],
            'status': row[5],
            'timestamp': row[6]
        })
    return jsonify(data)
