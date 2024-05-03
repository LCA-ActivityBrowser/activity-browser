"""
- ActivityBrowser.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 03/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    This Python script activates the Activity Browser environment and then runs the command "activity-browser"
    within that environment. It first constructs the path to the activation script based on the operating system,
    then executes the activation command using subprocess.run(). After running the "activity-browser" command, it
    deactivates the virtual environment by running the deactivation script using another subprocess.run() call.
"""

import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Activate the environment and run the activity-browser command
activateScript = os.path.join(envDir, "Scripts", "activate")
activateCmd = f"source {activateScript}" if os.name != "nt" else f"call {activateScript}"
subprocess.run(f"{activateCmd} && activity-browser", shell=True)

# Deactivate the environment and run the activity-browser command
deactivateScript = os.path.join(envDir, "Scripts", "deactivate")
deactivateCmd = f"source {deactivateScript}" if os.name != "nt" else f"call {deactivateScript}"
subprocess.run(deactivateCmd, shell=True)
