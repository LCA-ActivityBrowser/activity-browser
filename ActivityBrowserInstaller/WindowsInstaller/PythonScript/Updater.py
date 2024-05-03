import threading
import requests
import os
import re
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialog, QDesktopWidget
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

class DownloadThread(QObject):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self, user, repo):
        url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
        response = requests.get(url)
        data = response.json()

        if 'assets' not in data:
            self.update_label.emit("No 'assets' in the response data")
            return

        assets = data['assets']
        exeUrl = None
        for asset in assets:
            if asset['name'].endswith('.exe'):
                exeUrl = asset['browser_download_url']
                break

        if exeUrl is None:
            self.update_label.emit("No exe file found in the release")
            return

        response = requests.get(exeUrl, stream=True)
        if response.status_code == 200:
            with open("activity-browser.exe", 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            self.finished.emit()
        else:
            self.update_label.emit(f"Failed to download file: {response.status_code}")

class updaterWindow(QDialog):
    def __init__(self, parent=None):
        super(updaterWindow, self).__init__(parent)
        self.setWindowTitle("New Version Found!")
        self.resize(400, 200)
        self.center()
        self.download_thread = DownloadThread()
        self.download_thread.finished.connect(self.on_download_finished)

        # Check if we have the newest version of the Activity Browser installed.
        currentVersion = self.getActivityBrowserVersion()
        newestVersion = self.getLatestRelease(user="ThisIsSomeone", repo="activity-browser")
        isOldVersion = self.compare_versions(currentVersion, newestVersion)

        if not isOldVersion:
            # If not an old version, close the window
            self.close()
            return

        layout = QVBoxLayout()

        self.message_label = QLabel("A new version of the Activity Browser was found! "
                                    "Do you want to download and install the newest version now? "
                                    "You can also download other versions manually from "
                                    "<a href='https://github.com/LCA-ActivityBrowser/activity-browser'>"
                                    "https://github.com/LCA-ActivityBrowser/activity-browser</a>.")
        self.message_label.setOpenExternalLinks(True)
        layout.addWidget(self.message_label)

        button_layout = QHBoxLayout()
        remind_button = QPushButton("Remind me later")
        remind_button.clicked.connect(self.remind_later)
        install_button = QPushButton("Install now")
        install_button.clicked.connect(self.install_now)
        button_layout.addWidget(remind_button)
        button_layout.addWidget(install_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_label(self, message):
        self.message_label.setText(message)
        QApplication.processEvents()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def remind_later(self):
        self.close()

    def install_now(self):
        self.update_label("Downloading the installer for the newest version...")
        threading.Thread(target=self.download_thread.run, args=("ThisIsSomeone", "activity-browser")).start()

    def on_download_finished(self):
        self.update_label("Installer downloaded. Opening...")
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
            self.update_label("ActivityBrowser file not found in the directory.")
            return None
        except FileNotFoundError:
            self.update_label(f"Directory '{directory}' not found.")
            return None

    def compare_versions(self, version1, version2):
      """
      Compare two version strings in the format 'X.Y.Z' and determine if the second version is newer than the first.

      Parameters:
      - version1 (str): The first version string to compare.
      - version2 (str): The second version string to compare.

      Returns:
      - bool: True if version2 is newer than version1, False otherwise.
      """
      v1_components = [int(x) for x in version1.split('.')]
      v2_components = [int(x) for x in version2.split('.')]

      if v1_components[0] < v2_components[0]:
          return True
      elif v1_components[0] == v2_components[0]:
          if v1_components[1] < v2_components[1]:
              return True
          elif v1_components[1] == v2_components[1]:
              if v1_components[2] < v2_components[2]:
                  return True
      return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = updaterWindow()
    window.exec_()
    sys.exit(app.exec_())
