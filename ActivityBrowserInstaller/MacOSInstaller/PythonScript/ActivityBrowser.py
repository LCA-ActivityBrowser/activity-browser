import os
import sys
import subprocess
import argparse

def resourcePath(relativePath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, relativePath)

def runActivityBrowser(command, scriptPath):
    try:
        # Run the command using Python
        subprocess.run(["python"] + command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print(f"Error: The script '{scriptPath}' does not exist or is not accessible.")

def runUpdater():
    updaterPath = resourcePath('ActivityBrowser Updater.py')

    # Prepare the command
    command = [updaterPath]
    runActivityBrowser(command, updaterPath)

def openActivityBrowser(skipUpdateCheck):
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