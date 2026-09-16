import json
import logging
from app import create_app

# Load the debug setting from your config file
with open('config.json', 'r') as f:
    config_data = json.load(f)
    DEBUG_MODE = config_data.get("debug_mode", False)

# Initialize the Flask application using the factory
app = create_app()

if __name__ == '__main__':
    # Restore the original split-log architecture
    if DEBUG_MODE:
        file_handler = logging.FileHandler('app.debug.log')
        app.logger.setLevel(logging.DEBUG)
    else:
        file_handler = logging.FileHandler('app.log')
        app.logger.setLevel(logging.INFO)
        
    app.logger.addHandler(file_handler)
    app.logger.info('\n\n_______START OF SESSION_______\n\n')
    
    print(f"Starting server... (Debug Mode: {DEBUG_MODE})")
    
    # Launch the server
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE, use_reloader=DEBUG_MODE)
