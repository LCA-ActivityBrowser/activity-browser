from logging import getLogger

from qtpy.QtCore import Slot
from qtpy.QtWidgets import QHBoxLayout, QLabel, QStatusBar, QWidget

from activity_browser import signals
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


class Statusbar(QStatusBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.status_message_left = QLabel("Welcome")
        self.status_message_right = QLabel("Database")
        self.status_message_center = QLabel("Project")
        self.status_message_updates = QLabel("XXX")

        center_widget = QWidget()
        center_layout = QHBoxLayout()
        center_layout.setSpacing(12)
        center_layout.addWidget(self.status_message_center)
        center_layout.addWidget(self.status_message_updates)
        center_layout.addStretch()
        center_widget.setLayout(center_layout)

        self.addWidget(self.status_message_left, 1)
        self.addWidget(center_widget, 2)
        self.addWidget(self.status_message_right, 0)

        self.connect_signals()

    def connect_signals(self):
        signals.new_statusbar_message.connect(self.left)
        signals.project_updates_available.connect(self.updates_available)
        signals.project.changed.connect(self.update_project)
        signals.database_tab_open.connect(self.set_database)

    @Slot(str, name="statusLeft")
    def left(self, message: str) -> None:
        log.info(message)  # for console output
        if isinstance(message, str):
            # Only show the message for 10 seconds
            self.showMessage(message, 10 * 1000)

    @Slot(str, name="statusCenter")
    def center(self, message):
        self.status_message_center.setText(message)

    @Slot(str, name="statusRight")
    def right(self, message):
        self.status_message_right.setText(message)

    @Slot(name="updateProjectStatus")
    def update_project(self):
        self.center(f"Project: {bd.projects.current}")
        self.right("Database: None")
        self.status_message_updates.setText("")

    @Slot(str, name="setDatabaseName")
    def set_database(self, name):
        self.right("Database: {}".format(name))

    def updates_available(self, project_name: str, count: int):
        # If the project name does not match, just ignore it
        if project_name == bd.projects.current:
            if count > 0:
                self.status_message_updates.setText(f"{count} updates available")
            else:
                self.status_message_updates.setText("No updates available")
