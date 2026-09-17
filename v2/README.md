# 🎓 CS Lab Auto-Grader Platform

A lightweight, portable, and secure automated grading server designed for computer science and engineering laboratory environments. This platform safely evaluates student code submissions (C, C++, Java, Python, Bash) against hidden test cases using an isolated Docker sandbox.

## 🚀 Quick Start Guide

**1. Extract the Project**
Unzip the provided package onto your target lab server or local machine.

**2. Configure Security**
Open `config.json` and change the `"admin_pin"` to a secure, custom string. This acts as your login credential for the Teacher Dashboard.

**3. Launch the Server**
Open a terminal in the project directory, grant execution permissions to the startup script, and run it:
```bash
chmod +x start.sh
./start.sh

```

*Note: The script will automatically verify Docker, build the secure execution sandbox, create an isolated Python virtual environment, install dependencies, and launch the server on `http://0.0.0.0:5000`.*

## 🛠️ Core Features

* **Secure Sandboxing:** Student code strictly executes inside a network-isolated Docker container (`lab_sandbox`) to prevent malicious activity or system interference.
* **Web-Based Lab Manager:** Create new lab assignments, define allowed languages, and bulk-upload test cases (`input_X.txt`, `output_X.txt`) directly from the dashboard—no server restarts required.
* **Live Teacher Dashboard:** A real-time, searchable interface to monitor student progress, review raw code, run custom execution inputs, and view detailed compilation/runtime logs.
* **Smart File Architecture:** Student uploads are automatically organized into structured backend directories by lab session, department, and roll number.
* **One-Click Exports:** Export grading reports to CSV or download organized `.zip` archives of all student submissions for offline archiving.

## ⚙️ System Requirements

* **Docker:** Must be installed and running on the host machine. The user running the script must have Docker permissions.
* **Python 3.8+:** Required to run the Flask web application.

