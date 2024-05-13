"""
- ab_installer_test.py
- Date of File Creation: 10/05/2024
- Contributors: Ruben Visser
- Date and Author of Last Modification: 10/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    This Python script contains a unittest test case named TestEnvironmentExtraction. It sets up an environment,
    compresses a directory named "Scripts" into a tarball, and tests the extraction process.
    The test_environment_extraction method executes a Python script (ab_installer.py), checks if the extraction
    directory is created, and if files are correctly extracted.
"""

import os
import subprocess
import tarfile
import shutil
import pytest

@pytest.fixture(scope="module")
def setup_environment():
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

def test_environment_extraction(setup_environment):
    # Determine the path of the current directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set the path to the ab_installer.py based on the path of this test script
    ab_installer_path = os.path.join(current_dir, "..", "ActivityBrowserInstaller", "WindowsInstaller", "PythonScript", "ab_installer.py")

    # Run the installation code
    subprocess.run(["python", ab_installer_path])
    env_dir = "ActivityBrowserEnvironment"

    # Check if the directory is created
    assert os.path.exists(env_dir)

    # Check if files are extracted into the directory
    assert os.path.exists(os.path.join(env_dir, "Scripts"))
