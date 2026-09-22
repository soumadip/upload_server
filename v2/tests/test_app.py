import io
import os
import sqlite3
import json

# --- HELPER FUNCTIONS ---
def login_student(client, roll_no='11', enroll_no='ENR123'):
    """Helper to establish a valid student session."""
    return client.post('/setup', data={
        'name': 'Test Student', 'dept': 'TEST_DEPT', 'roll_no': roll_no,
        'enrollment_no': enroll_no, 'enrollment_no_confirm': enroll_no
    }, follow_redirects=True)

def login_admin(client):
    """Helper to establish a valid admin session."""
    return client.post('/admin/', data={'pin': '9999'}, follow_redirects=True)

def upload_dummy_file(client, filename, content=b"int main() { return 0; }"):
    """Helper to simulate a file upload."""
    return client.post('/upload', data={
        'files': (io.BytesIO(content), filename)
    }, content_type='multipart/form-data', follow_redirects=True)

# --- STUDENT ROUTES TESTS ---
def test_student_login_flow(client):
    """Test if a student can successfully initialize a session."""
    response = login_student(client)
    assert response.status_code == 200
    assert b'You are now logged in' in response.data
    assert b'Upload Code' in response.data

def test_file_upload_success_and_db_logging(client):
    """Test valid file upload, compilation handling, and database insertion."""
    login_student(client)
    
    # Upload a valid C file
    response = upload_dummy_file(client, 'test_algo.c')
    
    # Check flash message (it may compile or fail depending on test env gcc, but it should upload)
    assert b'uploaded' in response.data
    
    # Verify DB insertion
    conn = sqlite3.connect('lab_sessions.db')
    record = conn.execute("SELECT filename, dept, roll_no FROM submissions").fetchone()
    conn.close()
    
    assert record is not None
    assert 'test_algo.c' in record[0]
    assert record[1] == 'TEST_DEPT'
    assert record[2] == '11'

def test_file_upload_rejection(client):
    """Test if the system correctly rejects unauthorized file types based on config."""
    login_student(client)
    
    # Attempt to upload an unauthorized file
    response = upload_dummy_file(client, 'malicious_script.txt', b"echo 'hack'")
    
    assert b'Invalid file type' in response.data
    
    # Verify DB remains empty
    conn = sqlite3.connect('lab_sessions.db')
    count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    assert count == 0

def test_student_file_deletion(client):
    """Test if a student can delete their own active session file."""
    login_student(client)
    upload_dummy_file(client, 'to_delete.c')
    
    # Get the generated filename from DB to delete it
    conn = sqlite3.connect('lab_sessions.db')
    saved_filename = conn.execute("SELECT filename FROM submissions").fetchone()[0]
    
    # Delete the file via the route
    response = client.post(f'/delete/{saved_filename}', follow_redirects=True)
    assert b'File deleted successfully' in response.data
    
    # Verify deletion from DB
    count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    assert count == 0

# --- NEW: ADVANCED FEATURE TESTS ---
def test_global_submissions_lock(client):
    """Test if toggling the global lock prevents student uploads."""
    login_admin(client)
    
    # 1. Lock the lab
    res_lock = client.post('/admin/api/toggle_submissions')
    assert res_lock.json['is_open'] == False
    
    # 2. Attempt student upload
    login_student(client)
    res_upload = upload_dummy_file(client, 'locked_test.c')
    
    # 3. Verify rejection and empty database
    assert b'Submissions are currently closed' in res_upload.data
    conn = sqlite3.connect('lab_sessions.db')
    count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    assert count == 0

def test_admin_bulk_actions(client):
    """Test bulk regrade and bulk delete functionality."""
    # 1. Create multiple submissions
    login_student(client)
    upload_dummy_file(client, 'file1.c')
    upload_dummy_file(client, 'file2.c')
    
    conn = sqlite3.connect('lab_sessions.db')
    ids = [row[0] for row in conn.execute("SELECT id FROM submissions").fetchall()]
    conn.close()
    
    login_admin(client)
    
    # 2. Test Bulk Regrade
    res_regrade = client.post('/admin/api/bulk_action', json={'action': 'regrade', 'ids': ids})
    assert res_regrade.json['status'] == 'success'
    
    conn = sqlite3.connect('lab_sessions.db')
    statuses = [row[0] for row in conn.execute("SELECT status FROM submissions").fetchall()]
    conn.close()
    assert all(s == 'Pending Evaluation' for s in statuses)
    
    # 3. Test Bulk Delete
    res_delete = client.post('/admin/api/bulk_action', json={'action': 'delete', 'ids': ids})
    assert res_delete.json['status'] == 'success'
    
    conn = sqlite3.connect('lab_sessions.db')
    count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    assert count == 0

def test_plagiarism_engine(client):
    """Test if the structural plagiarism engine detects duplicated code."""
    # Code long enough to bypass the 20-character minimum threshold
    code_content = b"int main() {\n  printf(\"hello world\");\n  return 0;\n}\n// Shared comment"
    
    # Student A uploads
    login_student(client, roll_no='11', enroll_no='ENR111')
    upload_dummy_file(client, 'student_a.c', content=code_content)
    
    # Student B uploads the identical code
    login_student(client, roll_no='22', enroll_no='ENR222')
    upload_dummy_file(client, 'student_b.c', content=code_content)
    
    # Admin triggers the checker
    login_admin(client)
    res = client.get('/admin/api/check_similarity')
    data = res.json['data']
    
    # Verify the match was caught and scored correctly
    assert len(data) == 1
    match = data[0]
    assert match['student1'] in ['11', '22']
    assert match['student2'] in ['11', '22']
    assert match['similarity'] > 95.0

def test_admin_create_lab(client):
    """Test if an admin can create a new lab and correctly update the config and filesystem."""
    login_admin(client)
    
    # Create the lab via API
    res = client.post('/admin/api/create_lab', json={
        'lab_name': 'pytest_lab_02',
        'extensions': ['py', 'java']
    })
    assert res.json['status'] == 'success'
    
    # 1. Verify filesystem directory generation
    assert os.path.isdir(os.path.join('test_cases', 'pytest_lab_02'))
    
    # 2. Verify config.json mutation
    with open('config.json', 'r') as f:
        config = json.load(f)
    assert 'pytest_lab_02' in config['lab_extensions']
    assert config['lab_extensions']['pytest_lab_02'] == ['py', 'java']

# --- EXISTING ADMIN ROUTES TESTS ---
def test_admin_dashboard_security(client):
    """Test if the admin dashboard strictly requires the correct PIN."""
    res_no_pin = client.get('/admin/')
    assert b'Enter Admin PIN:' in res_no_pin.data  
    
    res_wrong = client.post('/admin/', data={'pin': '0000'}, follow_redirects=True)
    assert b'Invalid PIN' in res_wrong.data
    
    res_correct = login_admin(client)
    assert b'Teacher Dashboard' in res_correct.data

def test_admin_api_submissions(client):
    """Test if the AJAX endpoint returns the correct JSON data."""
    # Insert a record as a student
    login_student(client)
    upload_dummy_file(client, 'json_test.c')
    
    # Fetch as admin
    login_admin(client)
    response = client.get('/admin/api/submissions')
    
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    
    assert len(data) == 1
    assert data[0]['roll_no'] == '11'
    assert data[0]['enrollment_no'] == 'ENR123'
    assert 'json_test.c' in data[0]['filename']

def test_admin_exports(client):
    """Test if the CSV export and ZIP download routes generate valid files."""
    login_student(client)
    upload_dummy_file(client, 'export_test.c')
    login_admin(client)
    
    # Test CSV
    csv_res = client.get('/admin/export_csv')
    assert csv_res.status_code == 200
    assert csv_res.mimetype == 'text/csv'
    assert b'export_test.c' in csv_res.data
    
    # Test ZIP
    zip_res = client.get('/admin/download_zip')
    assert zip_res.status_code == 200
    assert zip_res.mimetype == 'application/zip'
