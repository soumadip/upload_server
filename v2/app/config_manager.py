import json
import os

def create_new_lab(app, lab_name, extensions):
    """Updates config.json and generates the required backend directories."""
    config_path = 'config.json'

    # 1. Update the JSON file permanently
    with open(config_path, 'r+') as f:
        config = json.load(f)
        if 'lab_extensions' not in config:
            config['lab_extensions'] = {}

        config['lab_extensions'][lab_name] = extensions

        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()

    # 2. Update Flask's live memory so no restart is needed
    if 'LAB_EXTENSIONS' not in app.config:
        app.config['LAB_EXTENSIONS'] = {}
    app.config['LAB_EXTENSIONS'][lab_name] = extensions

    # 3. Create the test_cases directory automatically
    os.makedirs(os.path.join('test_cases', lab_name), exist_ok=True)
    return True

def set_active_lab(app, lab_name):
    config_path = 'config.json'
    with open(config_path, 'r+') as f:
        config = json.load(f)
        config['active_lab'] = lab_name
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()

    app.config['ACTIVE_LAB'] = lab_name
    return True

