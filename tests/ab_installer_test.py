#ab_installer_test.py
#Made on 10/05/2024
#Contributed by Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#This Python script contains a unittest test case named TestEnvironmentExtraction. It sets up an environment,
#compresses a directory named "Scripts" into a tarball, and tests the extraction process.
#The test_environment_extraction method executes a Python script (ab_installer.py), checks if the extraction
#directory is created, and if files are correctly extracted.
#TODO: Update description

#Imports
import os
import subprocess
import tarfile
import shutil
import pytest

@pytest.fixture(scope="module")
def setupEnvironment():
    """
    Fixture to set up the environment for testing the ActivityBrowser installation process.

    This fixture creates a temporary directory named "Scripts" and a tarball file named "ActivityBrowser.tar.gz"
    containing the "Scripts" folder. It yields control to the test function.
    """
    if not os.path.exists("Scripts"):
        os.makedirs("Scripts")

    # Create a tarball file "ActivityBrowser.tar.gz" to simulate the installation process
    with tarfile.open("ActivityBrowser.tar.gz", "w:gz") as tar:
        # Add the "Scripts" folder to the Tarball file to check whether the tar unpacks correctly
        tar.add("Scripts", arcname="Scripts")

    yield

    # Delete all the created folders and Tarball file
    shutil.rmtree("Scripts")
    shutil.rmtree("ActivityBrowserEnvironment")
    os.remove("ActivityBrowser.tar.gz")

def test_environment_extraction(setupEnvironment):
    """
    Test case to verify the extraction of environment files during the ActivityBrowser installation process.

    This test function uses the `setupEnvironment` fixture to set up a test environment with a tarball file
    containing the "Scripts" folder. Then it runs the ActivityBrowser installation script and verifies that
    the "ActivityBrowserEnvironment" directory is created and files are extracted into it.

    Args:
        setupEnvironment: Fixture to set up the environment for testing.
    """
    # Determine the path of the current directory where this script is located
    currentDir = os.path.dirname(os.path.abspath(__file__))
    # Set the path to the ab_installer.py based on the path of this test script
    abInstallerPath = os.path.join(currentDir, "..", "ActivityBrowserInstaller", "PythonScript", "ab_installer.py")

    # Run the installation code
    subprocess.run(["python", abInstallerPath])
    envDir = "ActivityBrowserEnvironment"

    # Check if the directory is created
    assert os.path.exists(envDir)

    # Check if files are extracted into the directory
    assert os.path.exists(os.path.join(envDir, "Scripts"))
