from logging import getLogger

from PySide2.QtCore import Slot
from PySide2.QtWidgets import QLabel, QStatusBar

from activity_browser import signals
from activity_browser.i18n import _
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


class Statusbar(QStatusBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.status_message_left = QLabel(_("Welcome"))
        self.status_message_right = QLabel(_("Database"))
        self.status_message_center = QLabel(_("Project"))

        self.addWidget(self.status_message_left, 1)
        self.addWidget(self.status_message_center, 2)
        self.addWidget(self.status_message_right, 0)

        self.connect_signals()

    def connect_signals(self):
        signals.new_statusbar_message.connect(self.left)
        bd.projects.current_changed.connect(self.update_project)
        signals.database_tab_open.connect(self.set_database)

    @Slot(str, name="statusLeft")
    def left(self, message: str) -> None:
        log.info(message)  # for console output
        if isinstance(message, str):
            self.status_message_left.setText(message)

    @Slot(str, name="statusCenter")
    def center(self, message):
        self.status_message_center.setText(message)

    @Slot(str, name="statusRight")
    def right(self, message):
        self.status_message_right.setText(message)

    @Slot(name="updateProjectStatus")
    def update_project(self):
        self.center(_("Project: {project}", project=bd.projects.current))
        self.right(_("Database: None"))

    @Slot(str, name="setDatabaseName")
    def set_database(self, name):
        self.right(_("Database: {database}", database=name))
