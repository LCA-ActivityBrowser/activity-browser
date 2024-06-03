#ab_uninstaller.py
#Made on 22/04/2024
#Contributed by Thijs Groeneweg and Ruben Visser
#Last edited on 03/06/2024

#This Python script first obtains the current working directory and then constructs a path for a directory named
#"ActivityBrowserEnvironment" within that directory. It then attempts to remove this directory using shutil.rmtree().
#If the directory is successfully removed, it prints a success message indicating the directory's removal.
#If the directory is not found, it prints a message indicating that the directory was not found.



"""
- ab_installer.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 03/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    This Python script creates a directory named "ActivityBrowserEnvironment" and then extracts the
    contents of the compressed tar file "ActivityBrowser.tar.gz" into that directory using the tar command.
"""

#Imports
import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Create the environment directory
os.makedirs(envDir, exist_ok=True) 

# Extract the environment
subprocess.run(["tar", "-xzf", "ActivityBrowser.tar.gz", "-C", envDir])
