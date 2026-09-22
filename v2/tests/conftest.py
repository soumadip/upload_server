import pytest
import os
import json
import shutil
from app import create_app, init_db

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
    # 1. Grab the real path to your HTML templates BEFORE we isolate Flask
    real_templates = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'templates'))
    
    # 2. Spin up the Flask app
    app = create_app()
    
    # 3. Restrict the root path so config and test_cases stay inside the temp folder
    app.root_path = os.path.join(os.getcwd(), 'app')
    os.makedirs(app.root_path, exist_ok=True)
    
    # 4. Clone the HTML templates into the temp folder so Flask can render them
    shutil.copytree(real_templates, os.path.join(app.root_path, 'templates'))
    
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False 
    })
    
    # 5. Initialize the test database in the temp folder
    with app.app_context():
        init_db()
        
    yield app

@pytest.fixture
def client(app):
    # This acts as our "fake browser" to simulate student/teacher clicks
    # It automatically uses '127.0.0.1', which passes your IP whitelist!
    return app.test_client()
