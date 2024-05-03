"""
- ab_installer.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 03/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    This Python script creates a directory named "ActivityBrowserEnvironment" and then extracts the
    contents of the compressed tar file "ActivityBrowser.tar.gz" into that directory using the tar command.
"""

import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Create the environment directory
os.makedirs(envDir, exist_ok=True)  # Create directory with intermediate folders if needed

# Extract the environment
subprocess.run(["tar", "-xzf", "ActivityBrowser.tar.gz", "-C", envDir])
