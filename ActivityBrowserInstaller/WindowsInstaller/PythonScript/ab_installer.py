import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Create the environment directory
os.makedirs(envDir, exist_ok=True)  # Create directory with intermediate folders if needed

# Extract the environment
subprocess.run(["tar", "-xzf", "ActivityBrowser.tar.gz", "-C", envDir])
