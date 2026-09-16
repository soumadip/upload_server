import pytest
import os
import json
from app import create_app, init_db

# This fixture creates a completely isolated environment for every test run
@pytest.fixture(autouse=True)
def isolated_filesystem(tmp_path, monkeypatch):
    # Move the test execution into a temporary directory
    monkeypatch.chdir(tmp_path)
    
    # Create a dummy config.json for the tests
    test_config = {
        "active_lab": "pytest_lab_01",
        "admin_pin": "9999",
        "session_timeout_seconds": 1200,
        "departments": ["TEST_DEPT"],
        "lab_extensions": {
            "pytest_lab_01": ["c", "cpp"]
        }
    }
    with open("config.json", "w") as f:
        json.dump(test_config, f)

@pytest.fixture
def app():
    # Spin up the Flask app in the isolated directory
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False # Helpful if you add Flask-WTF forms later
    })
    
    # Initialize the test database in the temp folder
    with app.app_context():
        init_db()
        
    yield app

@pytest.fixture
def client(app):
    # This acts as our "fake browser" to simulate student/teacher clicks
    # It automatically uses '127.0.0.1', which passes your IP whitelist!
    return app.test_client()
