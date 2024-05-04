"""
- ActivityBrowser.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 03/05/2024 - Thijs Groeneweg
- Synopsis of the File's purpose:
    This Python script activates the Activity Browser environment and then runs the command "activity-browser"
    within that environment. It first constructs the path to the activation script based on the operating system,
    then executes the activation command using subprocess.run(). After running the "activity-browser" command, it
    deactivates the virtual environment by running the deactivation script using another subprocess.run() call.
"""

import os
import subprocess
import re
import requests

def getLatestRelease(user, repo):
        # Get the most recent version of the Activity Browser from the GitHub API.
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = requests.get(url)
        data = response.json()
        return data['tag_name']

def getActivityBrowserVersion(directory="."):
    # Get the version number of the ActivityBrowser file in the specified directory.
    try:
        for filename in os.listdir(directory):
            match = re.match(r'ActivityBrowser-(\d+\.\d+\.\d+)', filename)
            if match:
                return match.group(1)
        print("ActivityBrowser file not found in the directory.")
        return None
    except FileNotFoundError:
        print(f"Directory '{directory}' not found.")
        return None

def compareVersions(version1, version2):
    """
    Compare two version strings in the format 'X.Y.Z' and determine if the second version is newer than the first.

    Parameters:
    - version1 (str): The first version string to compare.
    - version2 (str): The second version string to compare.

    Returns:
    - bool: True if version2 is newer than version1, False otherwise.
    """
    if version1 is None or version2 is None:
        return False
    
    v1Components = [int(x) for x in version1.split('.')]
    v2Components = [int(x) for x in version2.split('.')]

    if v1Components[0] < v2Components[0]:
        return True
    elif v1Components[0] == v2Components[0]:
        if v1Components[1] < v2Components[1]:
            return True
        elif v1Components[1] == v2Components[1]:
            if v1Components[2] < v2Components[2]:
                return True
    return False

# Define environment directory
envDir = "ActivityBrowserEnvironment"

newestVersion = getLatestRelease("ThisIsSomeone", "activity-browser")
installedVersion = getActivityBrowserVersion()
isOldVersion = compareVersions(installedVersion, newestVersion)

if isOldVersion:
    subprocess.run("powershell Start-Process 'Updater.exe' -Verb runAs", shell=True)
else:
    # Activate the environment and run the activity-browser command
    activateScript = os.path.join(envDir, "Scripts", "activate")
    activateCmd = f"source {activateScript}" if os.name != "nt" else f"call {activateScript}"
    subprocess.run(f"{activateCmd} && activity-browser", shell=True)

    # Deactivate the environment and run the activity-browser command
    deactivateScript = os.path.join(envDir, "Scripts", "deactivate")
    deactivateCmd = f"source {deactivateScript}" if os.name != "nt" else f"call {deactivateScript}"
    subprocess.run(deactivateCmd, shell=True)
