import os
import subprocess

# Get the current directory
current_dir = os.getcwd()

# Create environment ab
create_env_command = f"conda create -n ActivityBrowser -c conda-forge --solver libmamba activity-browser --yes"
subprocess.run(create_env_command, shell=True, check=True)

