#ab_updater_test.py
#Made on 13/05/2024
#Contributed by Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#The Python script updates and verifies the download of an activity browser using external modules. It checks for
#the presence of the downloaded executable file in the temporary directory and provides a test function
#to validate the download process.
#TODO: Update description

#Imports
import os
import tempfile
import sys
import PySide2
import platform
import pytest

OPERATING_SYSTEM = platform.system()
if OPERATING_SYSTEM == "Windows" or OPERATING_SYSTEM == "Darwin":
    activity_browser_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ActivityBrowserInstaller", "PythonScript"))
    sys.path.append(activity_browser_path)
    updater = __import__("ActivityBrowser Updater")
    downloadThread = updater.downloadThread()

def checkDownload():
    """
    Checks the download of the activity browser executable.

    Downloads the Activity Browser using an updater thread and verifies
    the presence of the downloaded executable file 'activity-browser.exe'
    in the temporary directory.
    """
    OPERATING_SYSTEM = platform.system()
    if OPERATING_SYSTEM == "Windows" or OPERATING_SYSTEM == "Darwin":
        downloadThread.run(user="ThisIsSomeone", repo="activity-browser")
        temp_dir = tempfile.gettempdir()
        files = os.listdir(temp_dir)
        if OPERATING_SYSTEM == "Windows":
            assert "activity-browser.exe" in files
        elif OPERATING_SYSTEM == "Darwin":
            assert "activity-browser.app.zip" in files
    else:
        assert True

def test_checkDownload():
    """
    Tests the download verification process.

    Calls the checkDownload function to verify the download of the
    activity browser executable and asserts the presence of the file.
    """
    checkDownload()



