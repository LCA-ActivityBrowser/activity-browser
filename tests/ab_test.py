#ab_test.py
#Made on 17/05/2024
#Contributed by Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#This file has Python functions to test version management of an activity browser. It imports functions from
#'ActivityBrowser' to get the latest release version and the currently installed one. Key functions:
#delete_file(filename) removes a file, createOldVersion() makes an old version of the executable, createNewVersion()
#makes a new one, and there are tests to check version control.
#TODO: Update description

import os
import sys
activity_browser_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ActivityBrowserInstaller", "PythonScript"))
sys.path.append(activity_browser_path)
from ActivityBrowser import getLatestRelease, getActivityBrowserVersion, isSecondIputVersionNewer

currentVersion = getLatestRelease("ThisIsSomeone", "activity-browser")

def delete_file(filename):
    """
    Delete a file if it exists.

    Args:
        filename (str): The name of the file to be deleted.
    """
    if os.path.exists(filename):
        os.remove(filename)
        print(f"{filename} is deleted.")
    else:
        print(f"{filename} does not exist.")

def createOldVersion():
    """
    Create a dummy old version of the activity browser executable file.
    """
    currentDirectory = os.getcwd()
    dummyFilePath = os.path.join(currentDirectory, "ActivityBrowser-0.0.0.exe")
    open(dummyFilePath, "a").close()

def createNewVersion():
    """
    Create a dummy new version of the activity browser executable file.
    """
    currentDirectory = os.getcwd()
    dummyFilePath = os.path.join(currentDirectory, "ActivityBrowser-9.9.9.exe")
    open(dummyFilePath, "a").close()

def testOfGetVersion():
    """
    Test the functionality of getActivityBrowserVersion() function.
    It checks if the installed version is correctly retrieved.
    """
    createOldVersion()
    installedVersion = getActivityBrowserVersion()
    assert installedVersion == "0.0.0"
    delete_file("ActivityBrowser-0.0.0.exe")

def testTrue():
    """
    Test the functionality of isSecondIputVersionNewer() function.
    It checks if the function correctly identifies a newer version.
    """
    createOldVersion()
    installedVersion = getActivityBrowserVersion()
    assert isSecondIputVersionNewer(installedVersion, currentVersion)
    delete_file("ActivityBrowser-0.0.0.exe")

def testFalse():
    """
    Test the functionality of isSecondIputVersionNewer() function.
    It checks if the function correctly identifies that a version
    is not newer than the current version.
    """
    createNewVersion()
    installedVersion = getActivityBrowserVersion()
    assert not isSecondIputVersionNewer(installedVersion, currentVersion)
    delete_file("ActivityBrowser-9.9.9.exe")


