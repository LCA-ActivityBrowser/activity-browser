# -*- coding: utf-8 -*-
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QLabel, QStatusBar

import brightway2 as bw

from ..signals import signals
from ..logger import log

class Statusbar(QStatusBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.status_message_left = QLabel('Welcome')
        self.status_message_right = QLabel('Database')
        self.status_message_center = QLabel('Project')

        self.addWidget(self.status_message_left, 1)
        self.addWidget(self.status_message_center, 2)
        self.addWidget(self.status_message_right, 0)

        self.connect_signals()

    def connect_signals(self):
        signals.new_statusbar_message.connect(self.left)
        signals.project_selected.connect(self.update_project)
        signals.database_selected.connect(self.set_database)

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
        name = bw.projects.current
        self.center("Project: {}".format(name))
        self.right("Database: None")

    @Slot(str, name="setDatabaseName")
    def set_database(self, name):
        self.right("Database: {}".format(name))
