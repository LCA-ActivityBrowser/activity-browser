#ab_uninstaller_test.py
#Made on 17/05/2024
#Contributed by Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#The Python script is a unit test script designed to verify the functionality of an uninstallation script
#("ab_uninstaller.py") for an application. It sets up a test environment, creates a dummy file, and tests whether
#the uninstallation script removes a specified directory ("ActivityBrowserEnvironment").
#TODO: Update description

import os
import subprocess
import pytest

@pytest.fixture(scope="module")
def setupEnvironment():
    """
    Fixture to set up a dummy ActivityBrowser environment for testing.

    This fixture creates a temporary directory named "ActivityBrowserEnvironment" and a dummy
    ActivityBrowser executable file named "ActivityBrowser-Test.exe" for testing purposes. It yields the
    path of the temporary directory.

    Yields:
        str: The path of the temporary directory.
    """
    # Create a dummy ActivityBrowser environment for testing
    testDir = "ActivityBrowserEnvironment"
    os.makedirs(testDir)

    currentDirectory = os.getcwd()

    # Create a dummy ActivityBrowser exe file for testing in the current directory
    dummyFilePath = os.path.join(currentDirectory, "ActivityBrowser-Test.exe")
    open(dummyFilePath, "a").close()

    yield testDir

    # Clean up after the test
    if os.path.exists(testDir):
        os.rmdir(testDir)
    if os.path.exists(dummyFilePath):
        os.remove(dummyFilePath)

def testUninstall(setupEnvironment):
    """
    Test case to verify the uninstallation of the ActivityBrowser.

    This test function uses the `setup_environment` fixture to set up a test environment with a dummy
    ActivityBrowser installation. Then it runs the ActivityBrowser uninstallation script and verifies that the
    temporary directory and the dummy executable file are removed.

    Args:
        setup_environment (str): The path of the temporary directory created by the `setup_environment` fixture.
    """
    # Determine the path of the current directory where this script is located
    currentDir = os.path.dirname(os.path.abspath(__file__))
    # Set the path to the ab_installer.py based on the path of this test script
    abUninstallerPath = os.path.join(currentDir, "..", "ActivityBrowserInstaller", "PythonScript", "ab_uninstaller.py")

    # Run the uninstall script
    subprocess.run(["python", abUninstallerPath])
    # Check if the environment and the exe file is removed
    assert not os.path.exists(setupEnvironment), f"Directory '{setupEnvironment}' should be removed."


