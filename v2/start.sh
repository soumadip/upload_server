#!/bin/bash

echo "🚀 Initializing Lab Submission Server..."

# 1. Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 2. Check Docker permissions
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running or you lack permissions."
    echo "💡 Try running: sudo chmod 666 /var/run/docker.sock"
    exit 1
fi

# 3. Build the Docker sandbox if it doesn't exist yet
if [[ "$(docker images -q lab_sandbox 2> /dev/null)" == "" ]]; then
    echo "📦 Building the secure lab_sandbox Docker image (this takes a minute)..."
    docker build -t lab_sandbox -f Dockerfile.eval .
else
    echo "✅ lab_sandbox Docker image is ready."
fi

# 4. Setup an isolated Python Virtual Environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📥 Verifying dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# 5. Start the Server
echo "🌟 Starting Flask Server on http://0.0.0.0:5000"
python3 run.py
