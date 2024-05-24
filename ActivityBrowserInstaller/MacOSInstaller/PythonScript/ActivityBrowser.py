import os
import sys
import subprocess
import argparse
import subprocess

def resourcePath(relativePath):
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
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, relativePath)

def runActivityBrowser(command, scriptPath):
    """
    Executes a given command to run a script, handling potential errors.

    This function attempts to run a command using Python's subprocess module. If an error occurs during the execution
    of the command, it handles specific exceptions and provides appropriate error messages.

    Parameters:
    command (str): The command to execute the script.
    scriptPath (str): The path to the script that is intended to be run.

    Returns:
    None

    Exceptions:
    subprocess.CalledProcessError: Prints an error message if the command execution fails.
    FileNotFoundError: Prints an error message if the specified script path does not exist or is not accessible.
    """
    try:
        # Run the command using Python
        subprocess.Popen(command)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print(f"Error: The script '{scriptPath}' does not exist or is not accessible.")

def runUpdater():
    """
    Executes the ActivityBrowser Updater script.

    This function locates the updater script using the `resourcePath` function and runs it using Python. The updater
    script is expected to be named 'ActivityBrowser Updater.py'.

    Parameters:
    None

    Returns:
    None
    """
    updaterPath = resourcePath('ActivityBrowser Updater.py')
    os.system(f'python "{updaterPath}"')

def openActivityBrowser(skipUpdateCheck):
    """
    Opens the ActivityBrowser, optionally skipping the update check.

    This function prepares the command to open the ActivityBrowser by locating the 'openActivityBrowser.sh' script.
    It then decides whether to run the updater or directly open the ActivityBrowser based on the `skipUpdateCheck` 
    parameter.

    Parameters:
    skipUpdateCheck (bool): If True, skips the update check and directly runs the ActivityBrowser. If False, 
                            runs the updater first.

    Returns:
    None
    """    
    baseDir = os.path.dirname(__file__)
    scriptPath = os.path.join(baseDir, 'openActivityBrowser.sh')

    # Prepare the command
    command = [scriptPath]
    if skipUpdateCheck:
        runActivityBrowser(command, scriptPath)
    else:
        # check updates. If remind me later is selected, the updater will run the AB
        runUpdater() 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Open Activity Browser.')
    parser.add_argument('--skip-update-check', action='store_true', help='Skip checking for updates.')
    args = parser.parse_args()

    openActivityBrowser(args.skip_update_check)
