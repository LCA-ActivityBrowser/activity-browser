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

import unittest
import os
import subprocess

class TestCleanupScript(unittest.TestCase):
    def setUp(self):
        # Create a dummy ActivityBrowser environment for testing
        self.test_dir = "ActivityBrowserEnvironment"
        os.makedirs(self.test_dir)

        current_directory = os.getcwd()

        # Create a dummy ActivityBrowser exe file for testing in the current directory
        dummy_file_path = os.path.join(current_directory, "ActivityBrowser-Test.exe")
        open(dummy_file_path, "a").close()

    def testUninstall(self):
        # Run the uninstall script
        subprocess.run(["python", "ab_uninstaller.py"])
        # Check if the environment and the exe file is removed
        self.assertFalse(os.path.exists(self.test_dir), f"Directory '{self.test_dir}' should be removed.")

if __name__ == "__main__":
    unittest.main()

