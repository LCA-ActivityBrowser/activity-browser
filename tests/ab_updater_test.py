"""
- ab_updater_test.py
- Date of File Creation: 13/05/2024
- Contributors: Ruben Visser
- Date and Author of Last Modification: 17/05/2024 - Ruben Visser
- Synopsis of the File's purpose:

"""
import os
import tempfile
import sys

activity_browser_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ActivityBrowserInstaller", "WindowsInstaller", "PythonScript"))
sys.path.append(activity_browser_path)
updater = __import__("ActivityBrowser Updater")
downloadThread = updater.downloadThread()

def checkDownload():
    downloadThread.run(user="ThisIsSomeone", repo="activity-browser")
    temp_dir = tempfile.gettempdir()
    files = os.listdir(temp_dir)
    assert "activity-browser.exe" in files

def test_checkDownload():
    checkDownload()



