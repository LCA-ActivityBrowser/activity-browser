"""
- ActivityBrowser.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 06/05/2024 - Thijs Groeneweg
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
from packaging.version import parse

def getLatestRelease(user: str, repo: str) -> str:
    """
         Get the most recent version of the Activity Browser from the GitHub API.

        Parameters:
        - user (str): GitHub username of the repository owner.
        - repo (str): Name of the GitHub repository.

        Returns:
        - str: The latest release version.
        """
    url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
    try:
        response = requests.get(url)
        data = response.json()
        return data['tag_name'] if 'tag_name' in data else None
    # Handle exceptions that may occur during the request if the user is offline or the server is down.
    except requests.exceptions.RequestException:
        return None
    
def getActivityBrowserVersion(directory: str = ".") -> str:
    """
        Get the version number of the ActivityBrowser file in the specified directory.

        Parameters:
        - directory (str): The directory to search for the ActivityBrowser file.

        Returns:
        - str: The version number of the ActivityBrowser file.
        """
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

def isSecondIputVersionNewer(version1: str, version2: str) -> bool: 
    """
    Compare two version strings in the format 'X.Y.Z' and determine if the second version is newer than the first.

    Parameters:
    - version1 (str): The first version string to compare.
    - version2 (str): The second version string to compare.

    Returns:
    - bool: True if version2 is newer than version1, False otherwise. Returns False if either version is None.
    """
    if version1 is None or version2 is None:
        return False
    return parse(version1) < parse(version2)

def runActivityBrowser() -> None:
    """
    Activate the Activity Browser environment and run the activity-browser.
    """
    # Activate the environment and run the activity-browser command
    activateScript = os.path.join("ActivityBrowserEnvironment", "Scripts", "activate")
    activateCmd = f"source {activateScript}" if os.name != "nt" else f"call {activateScript}"
    subprocess.run(f"{activateCmd} && activity-browser", shell=True)

    # Deactivate the environment and run the activity-browser command
    deactivateScript = os.path.join("ActivityBrowserEnvironment", "Scripts", "deactivate")
    deactivateCmd = f"source {deactivateScript}" if os.name != "nt" else f"call {deactivateScript}"

if __name__ == "__main__":
    # Check if the ActivityBrowser file is up to date
    newestVersion = getLatestRelease("ThisIsSomeone", "activity-browser")
    installedVersion = getActivityBrowserVersion()
    isOldVersion = isSecondIputVersionNewer(installedVersion, newestVersion)

    if isOldVersion:
        # Run the Updater.exe file to update the ActivityBrowser as administrator
        subprocess.run("powershell Start-Process 'Updater.exe' -Verb runAs", shell=True)
    else:
        runActivityBrowser()
