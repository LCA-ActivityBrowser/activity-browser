"""
- Updater.py
- Date of File Creation: 29/05/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 03/05/2024 - Ruben Visser
- Synopsis of the File's purpose:
    This Python script checks for updates of an application from a GitHub repository, prompts the user to install
    the latest version if available, and handles the download and installation process with a progress bar.
    There are two classes, downloadThread downloads the Activity Browser and the updaterWindow does everything for the
    UI. The downloadWindow has two events, to which the updateWindow listens to update the UI to change the download progress.
"""

import threading
import requests
import os
import re
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialog, QDesktopWidget, QProgressBar
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

class downloadThread(QObject):
    finished = pyqtSignal()
    progressChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self, user, repo):
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = requests.get(url)
        data = response.json()

        if 'assets' not in data:
            self.updateLabel.emit("No 'assets' in the response data")
            return

        assets = data['assets']
        exeUrl = None
        for asset in assets:
            if asset['name'].endswith('.exe'):
                exeUrl = asset['browser_download_url']
                break

        if exeUrl is None:
            self.updateLabel.emit("No exe file found in the release")
            return

        response = requests.get(exeUrl, stream=True)
        totalSize = int(response.headers.get('content-length', 0))
        bytesDownloaded = 0
        if response.status_code == 200:
            with open("activity-browser.exe", 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        bytesDownloaded += len(chunk)
                        progress = int(bytesDownloaded / totalSize * 100)
                        self.progressChanged.emit(progress)
            self.finished.emit()
        else:
            self.updateLabel.emit(f"Failed to download file: {response.status_code}")

class updaterWindow(QDialog):
    def __init__(self, parent=None):
        super(updaterWindow, self).__init__(parent)
        self.setWindowTitle("New Version Found!")
        self.resize(400, 200)
        self.center()
        self.downloadThread = downloadThread()
        self.downloadThread.finished.connect(self.onDownloadFinished)
        self.downloadThread.progressChanged.connect(self.updateProgress)

        # Check if we have the newest version of the Activity Browser installed.
        currentVersion = self.getActivityBrowserVersion()
        newestVersion = self.getLatestRelease(user="ThisIsSomeone", repo="activity-browser")
        isOldVersion = self.compareVersions(currentVersion, newestVersion)

        if not isOldVersion:
            # If not an old version, close the window
            self.close()
            return

        layout = QVBoxLayout()

        self.messageLabel = QLabel("A new version of the Activity Browser was found! "
                                    "Do you want to download and install the newest version now? "
                                    "You can also download other versions manually from "
                                    "<a href='https://github.com/LCA-ActivityBrowser/activity-browser'>"
                                    "https://github.com/LCA-ActivityBrowser/activity-browser</a>.")
        self.messageLabel.setOpenExternalLinks(True)
        layout.addWidget(self.messageLabel)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.hide()
        layout.addWidget(self.progressBar)

        buttonLayout = QHBoxLayout()
        remindButton = QPushButton("Remind me later")
        remindButton.clicked.connect(self.remindLater)
        installButton = QPushButton("Install now")
        installButton.clicked.connect(self.installNow)
        buttonLayout.addWidget(remindButton)
        buttonLayout.addWidget(installButton)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

    def updateLabel(self, message):
        self.messageLabel.setText(message)
        QApplication.processEvents()
    
    def showProgressBar(self):
        self.progressBar.show()
    
    def updateProgress(self, value):
        self.progressBar.setValue(value)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def remindLater(self):
        self.close()

    def installNow(self):
        self.updateLabel("Downloading the installer for the newest version...")
        self.showProgressBar()
        threading.Thread(target=self.downloadThread.run, args=("ThisIsSomeone", "activity-browser")).start()

    def onDownloadFinished(self):
        self.updateLabel("Installer downloaded. Opening...")
        os.startfile("activity-browser.exe")
        self.close()
        sys.exit()

    def getLatestRelease(self, user, repo):
        # Get the most recent version of the Activity Browser from the GitHub API.
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = requests.get(url)
        data = response.json()
        return data['tag_name']

    def getActivityBrowserVersion(self, directory="."):
        # Get the version number of the ActivityBrowser file in the specified directory.
        try:
            for filename in os.listdir(directory):
                match = re.match(r'ActivityBrowser-(\d+\.\d+\.\d+)', filename)
                if match:
                    return match.group(1)
            self.updateLabel("ActivityBrowser file not found in the directory.")
            return None
        except FileNotFoundError:
            self.updateLabel(f"Directory '{directory}' not found.")
            return None

    def compareVersions(self, version1, version2):
      """
      Compare two version strings in the format 'X.Y.Z' and determine if the second version is newer than the first.

      Parameters:
      - version1 (str): The first version string to compare.
      - version2 (str): The second version string to compare.

      Returns:
      - bool: True if version2 is newer than version1, False otherwise.
      """
      v1Components = [int(x) for x in version1.split('.')]
      v2Components = [int(x) for x in version2.split('.')]

      if v1Components[0] < v2Components[0]:
          return True
      elif v1Components[0] == v2Components[0]:
          if v1Components[1] < v2Components[1]:
              return True
          elif v1Components[1] == v2Components[1]:
              if v1Components[2] < v2Components[2]:
                  return True
      return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = updaterWindow()
    window.exec_()
    sys.exit(app.exec_())
