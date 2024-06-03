#ab_uninstaller.py
#Made on 22/04/2024
#Contributed by Thijs Groeneweg and Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#This Python script creates a directory named "ActivityBrowserEnvironment" and then extracts the
#contents of the compressed tar file "ActivityBrowser.tar.gz" into that directory using the tar command.
#TODO: Update description

#Imports
import os
import subprocess

# Define environment directory
envDir = "ActivityBrowserEnvironment"

# Create the environment directory
os.makedirs(envDir, exist_ok=True) 

# Extract the environment
subprocess.run(["tar", "-xzf", "ActivityBrowser.tar.gz", "-C", envDir])
