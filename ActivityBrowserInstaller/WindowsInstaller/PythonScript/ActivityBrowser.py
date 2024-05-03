import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Activate the environment and run the activity-browser command
activate_script = os.path.join(envDir, "Scripts", "activate")
activate_cmd = f"source {activate_script}" if os.name != "nt" else f"call {activate_script}"
subprocess.run(f"{activate_cmd} && activity-browser", shell=True)

# Deactivate the environment and run the activity-browser command
deactivate_script = os.path.join(envDir, "Scripts", "deactivate")
deactivate_cmd = f"source {deactivate_script}" if os.name != "nt" else f"call {deactivate_script}"
subprocess.run(deactivate_cmd, shell=True)
