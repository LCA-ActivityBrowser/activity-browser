"""
- ab_uninstaller.py
- Date of File Creation: 10/05/2024
- Contributors: Ruben Visser
- Date and Author of Last Modification: 10/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    The Python script is a unit test script designed to verify the functionality of an uninstallation script
    ("ab_uninstaller.py") for an application. It sets up a test environment, creates a dummy file, and tests whether
    the uninstallation script removes a specified directory ("ActivityBrowserEnvironment").
"""

import os
import subprocess
import pytest

@pytest.fixture(scope="module")
def setup_environment():
    # Create a dummy ActivityBrowser environment for testing
    test_dir = "ActivityBrowserEnvironment"
    os.makedirs(test_dir)

    current_directory = os.getcwd()

    # Create a dummy ActivityBrowser exe file for testing in the current directory
    dummy_file_path = os.path.join(current_directory, "ActivityBrowser-Test.exe")
    open(dummy_file_path, "a").close()

    yield test_dir

    # Clean up after the test
    if os.path.exists(test_dir):
        os.rmdir(test_dir)
    if os.path.exists(dummy_file_path):
        os.remove(dummy_file_path)

def test_uninstall(setup_environment):
    # Determine the path of the current directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set the path to the ab_installer.py based on the path of this test script
    ab_uninstaller_path = os.path.join(current_dir, "..", "ActivityBrowserInstaller", "PythonScript", "ab_uninstaller.py")
    # Run the uninstall script
    subprocess.run(["python", ab_uninstaller_path])
    # Check if the environment and the exe file is removed
    assert not os.path.exists(setup_environment), f"Directory '{setup_environment}' should be removed."


