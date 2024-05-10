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
import unittest
import tarfile
import shutil

class TestEnvironmentExtraction(unittest.TestCase):
    def setUp(self):
        if not os.path.exists("Scripts"):
            os.makedirs("Scripts")

        # Create a tarball file "ActivityBrowser.tar.gz" to simulate the installation process
        with tarfile.open("ActivityBrowser.tar.gz", "w:gz") as tar:
            # Add the "Scripts" folder to the Tarbal file to check whether the tar unpacks correctly
            tar.add("Scripts", arcname="Scripts")

    def tearDown(self):
        # Delete al the created folders and Tarbal file
        shutil.rmtree("Scripts")
        shutil.rmtree("ActivityBrowserEnvironment")
        os.remove("ActivityBrowser.tar.gz")

    def test_environment_extraction(self):
        # Run the installation code
        subprocess.run(["python", "ab_installer.py"])
        self.env_dir = "ActivityBrowserEnvironment"

        # Check if the directory is created
        self.assertTrue(os.path.exists(self.env_dir))

        # Check if files are extracted into the directory
        self.assertTrue(os.path.exists(os.path.join(self.env_dir, "Scripts")))

if __name__ == '__main__':
    unittest.main()
