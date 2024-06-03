#ActivityBrowser.py
#Made on 20/05/2024
#Contributed by Thijs Groeneweg and Bryan Owee
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#TODO: Description

#Imports
import os
import sys
import subprocess
import argparse
import platform
import re
import requests
from packaging.version import parse

def parseArgs():
    """
    Parse command line arguments.

    This function sets up an argument parser to handle command line arguments for running the Activity Browser. 
    It allows specifying '--skip-update-check' to skip checking for updates.
s
    Parameters:
    None

    Returns:
    argparse.Namespace: An object containing the parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run the Activity Browser.")
    parser.add_argument("--skip-update-check", action="store_true", help="Skip checking for updates.")
    return parser.parse_args()

def getLatestRelease(user: str, repo: str) -> str:
    """
    Get the most recent version of the Activity Browser from the GitHub API.

    This function queries the GitHub API to fetch information about the latest release of the Activity Browser 
    repository specified by the user and repository name. It returns the tag name of the latest release if 
    available, otherwise returns None.

    Parameters:
    user (str): The GitHub username or organization name.
    repo (str): The name of the GitHub repository.

    Returns:
    str or None: The tag name of the latest release, or None if the information cannot be retrieved.
    """
    url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
    try:
        response = requests.get(url)
        data = response.json()
        return data['tag_name'] if 'tag_name' in data else None
    except requests.exceptions.RequestException:
        return None

def getActivityBrowserVersion(directory: str = ".") -> str:
    """
    Get the version number of the ActivityBrowser file in the specified directory.

    This function searches for the ActivityBrowser file in the specified directory. It expects the file name to follow 
    the pattern 'ActivityBrowser-X.X.X', where X represents digits of the version number. If the file is found, it 
    returns the version number extracted from the file name. If the file is not found or the directory does not exist, 
    it prints an appropriate message and returns None.

    Parameters:
    directory (str): The directory to search for the ActivityBrowser file. Defaults to the current directory.

    Returns:
    str or None: The version number of the ActivityBrowser file, or None if the file is not found or the directory 
                 does not exist.
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
    Compare two version strings and determine if the second version is newer than the first.

    This function compares two version strings representing software versions. It returns True if the second version 
    is newer than the first version, and False otherwise. If either of the version strings is None, it returns False.

    Parameters:
    version1 (str): The first version string.
    version2 (str): The second version string.

    Returns:
    bool: True if the second version is newer, False otherwise.
    """
    if version1 is None or version2 is None:
        return False
    return parse(version1) < parse(version2)

def runActivityBrowserWindows(skipUpdateCheck) -> None:
    """
    Activate the Activity Browser environment and run the activity-browser on Windows.

    This function is specifically designed to run the Activity Browser environment and execute the activity-browser 
    application on Windows operating systems. It checks for updates and runs the updater if a newer version is available 
    or directly launches the activity-browser if the current version is up-to-date. If `skipUpdateCheck` is True, it 
    skips the update check and directly runs the activity-browser.

    Parameters:
    skipUpdateCheck (bool): If True, skips the update check and directly runs the activity-browser. If False, 
                            checks for updates and runs the updater if necessary.

    Returns:
    None
    """
    if not skipUpdateCheck:
        newestVersion = getLatestRelease("ThisIsSomeone", "activity-browser")
        installedVersion = getActivityBrowserVersion()
        isOldVersion = isSecondIputVersionNewer(installedVersion, newestVersion)

        if isOldVersion:
            runUpdaterWindows()
            
        else:
            runActivityBrowserCommandsWindows()
    else:
        runActivityBrowserCommandsWindows()

def runActivityBrowserCommandsWindows() -> None:
    """
    Run the activity-browser commands on Windows.

    This function activates the Activity Browser environment, runs the activity-browser application, and then deactivates 
    the environment. It is specifically designed for Windows operating systems.

    Parameters:
    None

    Returns:
    None
    """
    activate_script = os.path.join("ActivityBrowserEnvironment", "Scripts", "activate")
    deactivate_script = os.path.join("ActivityBrowserEnvironment", "Scripts", "deactivate")

    activate_cmd = f"call {activate_script}"
    deactivate_cmd = f"call {deactivate_script}"

    os.system(f"{activate_cmd} && activity-browser")
    os.system(f"{deactivate_cmd}")

def resourcePath(relativePath) -> str:
    """
    Get the absolute path to a resource, working for both development and PyInstaller environments.
    This function is used to locate resources in a way that works during development as well as when the application
    is packaged using PyInstaller. PyInstaller creates a temporary folder and stores the path to this folder in
    the _MEIPASS attribute.
    Parameters:
    relativePath (str): The relative path to the resource file.
    Returns:
    str: The absolute path to the resource.
    """
    try:
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, relativePath)

def runUpdaterWindows() -> None:
    """
    Run the ActivityBrowser Updater on Windows.

    This function attempts to run the ActivityBrowser Updater executable with elevated privileges using PowerShell's 
    Start-Process command. If an error occurs during the execution of the updater, it falls back to running the 
    activity-browser commands using `runActivityBrowserCommandsWindows`.

    Parameters:
    None

    Returns:
    None
    """
    try:
        subprocess.run(
            "powershell Start-Process 'ActivityBrowser Updater.exe' -Verb runAs",
            shell=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Failed to run the updater. Error code:", e.returncode)
        runActivityBrowserCommandsWindows()
    except Exception as e:
        print("An unexpected error occurred:", str(e))
        runActivityBrowserCommandsWindows()

def runUpdaterMac() -> None:
    """
    Run the ActivityBrowser Updater on macOS.

    This function attempts to run the ActivityBrowser Updater script. If an error occurs during the execution of the 
    updater, it prints an error message and falls back to opening the Activity Browser without performing the update.

    Parameters:
    None

    Returns:
    None
    """
    try:
        updaterPath = resourcePath('ActivityBrowser Updater.py')
        # Running the updater script using os.system and capturing the return code
        return_code = os.system(f'python "{updaterPath}"')
        if return_code != 0:
            print("Can not open the updater, did you decline the admin privileges?")
            openActivityBrowserMac(skipUpdateCheck=True)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        openActivityBrowserMac(skipUpdateCheck=True)

def openActivityBrowserMac(skipUpdateCheck) -> None:
    """
    Open the Activity Browser on macOS.

    This function prepares and executes the command to open the Activity Browser on macOS. If `skipUpdateCheck` is 
    True, it directly runs the command to open the Activity Browser. If False, it runs the updater before opening 
    the Activity Browser.

    Parameters:
    skipUpdateCheck (bool): If True, skips the update check and directly opens the Activity Browser. If False, 
                            runs the updater before opening the Activity Browser.

    Returns:
    None
    """
    baseDir = os.path.dirname(__file__)
    scriptPath = os.path.join(baseDir, 'openActivityBrowser.sh')

    command = [scriptPath]
    if skipUpdateCheck:
        try:
           subprocess.Popen(command)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
        except FileNotFoundError:
            print(f"Error: The script '{scriptPath}' does not exist or is not accessible.")
    else:
        runUpdaterMac()

def main() -> None:
    """
    Main function to run the Activity Browser application.

    This function parses command-line arguments, determines the operating system, and then either runs the Activity 
    Browser on Windows or opens it on macOS. If the operating system is unsupported, it prints an appropriate message.

    Parameters:
    None

    Returns:
    None
    """
    args = parseArgs()

    if platform.system() == "Windows":
        runActivityBrowserWindows(args.skip_update_check)
    elif platform.system() == "Darwin":  # macOS
        openActivityBrowserMac(args.skip_update_check)
    else:
        print("Unsupported operating system.")

if __name__ == "__main__":
    main()
