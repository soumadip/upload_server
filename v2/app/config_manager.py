import os
import json
from werkzeug.utils import secure_filename

def create_new_lab(app, new_lab_name, extensions):
    safe_lab = secure_filename(new_lab_name)

    # 1. Update the JSON config
    config_path = os.path.join(app.root_path, '..', 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    if safe_lab not in config['lab_extensions']:
        config['lab_extensions'][safe_lab] = extensions

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

    # 2. Create the physical directory for test cases
    test_dir = os.path.join(app.root_path, '..', 'test_cases', safe_lab)
    os.makedirs(test_dir, exist_ok=True)

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

