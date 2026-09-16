import io
import os
import sqlite3

def test_student_login_flow(client):
    """Test if a student can successfully initialize a session."""
    # Simulate a student submitting the setup form
    response = client.post('/setup', data={
        'name': 'John Doe',
        'dept': 'TEST_DEPT',
        'roll_no': '42',
        'enrollment_no': 'ENR123',
        'enrollment_no_confirm': 'ENR123'
    }, follow_redirects=True)
    
    # Check if the login flash message appears and they reach the upload page
    assert response.status_code == 200
    assert b'You are now logged in' in response.data
    assert b'Upload Code' in response.data

def test_file_upload_rejection(client):
    """Test if the system correctly rejects unauthorized file types based on config."""
    # 1. Log the student in
    client.post('/setup', data={
        'name': 'Jane Doe', 'dept': 'TEST_DEPT', 'roll_no': '11',
        'enrollment_no': 'ENR456', 'enrollment_no_confirm': 'ENR456'
    })
    
    # 2. Try to upload a .txt file (which is NOT in our test config allowed list)
    data = {
        'files': (io.BytesIO(b"Hello World"), 'malicious_script.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    # 3. Verify it was rejected
    assert b'Invalid file type' in response.data
    
    # 4. Verify nothing was saved to the database
    conn = sqlite3.connect('lab_sessions.db')
    count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    conn.close()
    assert count == 0

def test_admin_dashboard_security(client):
    """Test if the admin dashboard requires the correct PIN."""
    # Try accessing without a PIN
    res_no_pin = client.get('/admin/')
    assert b'Enter Admin PIN:' in res_no_pin.data  # Should show login screen
    assert b'Download All' not in res_no_pin.data  # Should hide protected buttons

    # Try accessing with the WRONG PIN
    res_wrong = client.post('/admin/', data={'pin': '0000'}, follow_redirects=True)
    assert b'Invalid PIN' in res_wrong.data
    
    # Try accessing with the CORRECT PIN (defined in our test conftest.py)
    res_correct = client.post('/admin/', data={'pin': '9999'}, follow_redirects=True)
    assert b'Teacher Dashboard' in res_correct.data
    assert b'Download All' in res_correct.data
