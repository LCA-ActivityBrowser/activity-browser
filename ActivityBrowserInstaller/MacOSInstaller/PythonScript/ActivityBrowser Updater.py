"""
- ActivityBrowser Updater.py
- Date of File Creation: 10/05/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 10/05/2024 - Thijs Groeneweg
- Synopsis of the File's purpose:
    This Python script checks for updates of an application from a GitHub repository, prompts the user to install
    the latest version if available, and handles the download and installation process with a progress bar.
    There are two classes, downloadThread downloads the Activity Browser and the updaterWindow does everything for the
    UI. The downloadWindow has two events, to which the updateWindow listens to update the UI to change the download progress.
"""

import tempfile
import threading
import subprocess
import re
from packaging.version import parse
import requests
import os
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialog, QDesktopWidget, QProgressBar
from PyQt5.QtCore import QObject, pyqtSignal

# Define constants
INSTALLER_FILENAME = "activity-browser.app"
TEMP_DIR = tempfile.gettempdir()

class downloadThread(QObject):
    finished = pyqtSignal()
    progressChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

    def getLatestReleaseData(self, user: str, repo: str) -> dict:
        """
        Fetches the latest release data for a given GitHub repository.

        Parameters:
        user (str): The username of the repository owner.
        repo (str): The name of the repository.

        Returns:
        dict: A dictionary containing the 'assets' data of the latest release. 
            If 'assets' is not present in the response data, emits an updateLabel signal with a message and returns None.
        """
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = requests.get(url)
        data = response.json()

        if 'assets' not in data:
            self.updateLabel.emit("No 'assets' in the response data")
            return None

        return data['assets']

    def findExeUrl(self, assets: list) -> str:
        """
        Finds the download URL of the .app file from the list of assets.

        Parameters:
        assets (list): A list of dictionaries, each representing an asset of a GitHub release.

        Returns:
        str: The download url of the .app file. If no .app file is found, emits an updateLabel signal with a message and returns None.
        """
        for asset in assets:
            if asset['name'].endswith('.app'):
                return asset['browser_download_url']

        self.updateLabel.emit("No app file found in the release")
        return None

    def downloadFile(self, url: str, filename: str) -> None:
        """
        Downloads a file from a given URL and saves it with a specified filename in a temporary directory.

        Parameters:
        url (str): The URL of the file to download.
        filename (str): The name to save the downloaded file as.

        Returns:
        None

        Emits:
        progressChanged: Emits the download progress as a percentage.
        finished: Emits when the download is complete.
        updateLabel: Emits a message if the download fails, with the HTTP status code.
        """
        # Get the total size of the file to download, so we can calculate the download progress
        try:
            response = requests.get(url, stream=True)
            totalSize = int(response.headers.get('content-length', 0))
            bytesDownloaded = 0
        except requests.exceptions.RequestException as e:
            self.updateLabel.emit(f"Failed to download file: {str(e)}")

        # Download the file in chunks and write it to the specified filename in a temporary directory
        if response.status_code == 200:
            file_path = os.path.join(TEMP_DIR, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        bytesDownloaded += len(chunk)
                        progress = int(bytesDownloaded / totalSize * 100)
                        self.progressChanged.emit(progress)
            self.finished.emit()
        else:
            # If the download fails, emit a signal with the HTTP status code
            self.updateLabel.emit(f"Failed to download file: {response.status_code}")

    def run(self, user: str, repo: str) -> None:
        """
        Runs the update process for a specified GitHub repository.

        This function fetches the latest release data for the repository, finds the download URL of the .app file in the release assets, and downloads the file.

        Parameters:
        user (str): The username of the repository owner.
        repo (str): The name of the repository.

        Returns:
        None

        If the latest release data does not contain any assets, or if no .app file is found in the assets, the function returns early.
        """
        try:
            assets = self.getLatestReleaseData(user, repo)
            if assets is None:
                return

            appUrl = self.findappUrl(assets)
            if appUrl is None:
                return

            self.downloadFile(appUrl, INSTALLER_FILENAME)
        except Exception as e:
            self.updateLabel.emit(f"An error occurred: {str(e)}")

class updaterWindow(QDialog):
    def __init__(self, user: str, repo: str, parent=None):
        super(updaterWindow, self).__init__(parent)
        self.user = user
        self.repo = repo
        self.setWindowTitle("New Version Found!")
        self.resize(400, 200)
        self.center()
        self.downloadThread = downloadThread()
        self.downloadThread.finished.connect(self.onDownloadFinished)
        self.downloadThread.progressChanged.connect(self.updateProgress)

        layout = QVBoxLayout()

        self.messageLabel = QLabel("A new version of the Activity Browser was found! "
                                    "Do you want to download and install the newest version now? "
                                    "You can also download other versions manually from "
                                    "<a href='https://github.com/LCA-ActivityBrowser/activity-browser'>"
                                    "https://github.com/LCA-ActivityBrowser/activity-browser</a>.")
        self.messageLabel.setOpenExternalLinks(True)
        layout.addWidget(self.messageLabel)

        # Check if we have the newest version of the Activity Browser installed.
        currentVersion = self.getActivityBrowserVersion()
        newestVersion = self.getLatestRelease(user="ThisIsSomeone", repo="activity-browser")
        isOldVersion = self.isSecondIputVersionNewer(currentVersion, newestVersion)

        if not isOldVersion:
            # If not an old version, close the window
            self.exitApplication()
            return

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.hide()
        layout.addWidget(self.progressBar)

        buttonLayout = QHBoxLayout()
        self.remindButton = QPushButton("Remind me later")
        self.remindButton.clicked.connect(self.remindLater)
        self.installButton = QPushButton("Install now")
        self.installButton.clicked.connect(self.installNow)
        buttonLayout.addWidget(self.remindButton)
        buttonLayout.addWidget(self.installButton)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
    
    def getLatestRelease(self, user: str, repo: str) -> str:
        """
         Get the most recent version of the Activity Browser from the GitHub API.

        Parameters:
        - user (str): GitHub username of the repository owner.
        - repo (str): Name of the GitHub repository.

        Returns:
        - str: The latest release version.
        """
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        try:
            response = requests.get(url)
            data = response.json()
            return data['tag_name'] if 'tag_name' in data else None
        # Handle exceptions that may occur during the request if the user is offline or the server is down.
        except requests.exceptions.RequestException:
            return None
    
    def getActivityBrowserVersion(self, directory: str = ".") -> str:
        """
            Get the version number of the ActivityBrowser file in the specified directory.

            Parameters:
            - directory (str): The directory to search for the ActivityBrowser file.

            Returns:
            - str: The version number of the ActivityBrowser file.
            """
        try:
            for filename in os.listdir(directory):
                match = re.match(r'ActivityBrowser-(\d+\.\d+\.\d+)', filename)
                if match:
                    return match.group(1)
            print("ActivityBrowser file not found in the directory.")
            return None
        except FileNotFoundError:
            print(f"Directory '{directory}' not found.")
            return None

    def isSecondIputVersionNewer(self, version1: str, version2: str) -> bool: 
        """
        Compare two version strings in the format 'X.Y.Z' and determine if the second version is newer than the first.

        Parameters:
        - version1 (str): The first version string to compare.
        - version2 (str): The second version string to compare.

        Returns:
        - bool: True if version2 is newer than version1, False otherwise. Returns False if either version is None.
        """
        if version1 is None or version2 is None:
            return False
        return parse(version1) < parse(version2)

    def getActivityBrowserFilename(self) -> str:
        """
        Get the filename of the ActivityBrowser executable in the current directory.

        Returns:
        - str: The filename of the ActivityBrowser executable.
        """
        for filename in os.listdir("."):
            if filename.startswith("ActivityBrowser-"):
                return filename
        return None

    def runActivityBrowser(self) -> None:
        """
        Activate the Activity Browser environment and run the activity-browser.
        """
        subprocess.run(["start", self.getActivityBrowserFilename(), "--skip-update-check"], check=True, shell=True)

    def updateLabel(self, message: str) -> None:
        """
        Update the message label with the specified text.

        Parameters:
        - message (str): The text to display in the message label.
        """
        self.messageLabel.setText(message)
        QApplication.processEvents()
    
    def showProgressBar(self) -> None:
        """Show the progress bar."""
        self.progressBar.show()
    
    def updateProgress(self, value: int) -> None:
        """
        Update the progress bar with the specified value.

        Parameters:
        - value (int): The value to set the progress bar to.
        """
        self.progressBar.setValue(value)

    def center(self) -> None:
        """Center the window on the screen."""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def installNow(self) -> None:
        """Initiate the download and installation process."""
        self.installButton.setDisabled(True)
        self.remindButton.setDisabled(True)
        self.updateLabel("Downloading the installer for the newest version...")
        self.showProgressBar()
        threading.Thread(target=self.downloadThread.run, args=(self.user, self.repo)).start()
    
    def exitApplication(self) -> None:
        """Close the window and exit the application."""
        self.close()
        sys.exit()
    
    def remindLater(self) -> None:
        """Open the Activity Browser and close the updater window."""
        self.hide()
        self.runActivityBrowser()
        self.exitApplication()

    def onDownloadFinished(self) -> None:
        """Open the installer after download completion and close the window."""
        self.updateLabel("Installer downloaded. Opening...")
        file_path = os.path.join(TEMP_DIR, INSTALLER_FILENAME)
        try:
            # Hide the updater window
            self.hide()
            # Start the installer
            subprocess.Popen([file_path])
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        self.exitApplication()

    def closeEvent(self, event) -> None:
        """
        Override the closeEvent method to call sys.exit() when the close button is clicked.
        """
        self.destroy()
        self.exitApplication()

if __name__ == "__main__":
    # Check if the script is running as an administrator for changing files in ActivityBrowser directory      
    app = QApplication(sys.argv)
    window = updaterWindow(user="ThisIsSomeone", repo="activity-browser")
    window.exec_()
    sys.exit(app.exec_())
