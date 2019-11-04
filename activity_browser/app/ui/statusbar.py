# -*- coding: utf-8 -*-
from PySide2 import QtWidgets

from brightway2 import projects

from ..signals import signals


class Statusbar(object):
    def __init__(self, window):
        self.window = window
        self.statusbar = QtWidgets.QStatusBar()
        self.window.setStatusBar(self.statusbar)

        self.status_message_left = QtWidgets.QLabel('Welcome')
        self.status_message_right = QtWidgets.QLabel('Database')
        self.status_message_center = QtWidgets.QLabel('Project')

        self.statusbar.addWidget(self.status_message_left, 1)
        self.statusbar.addWidget(self.status_message_center, 2)
        self.statusbar.addWidget(self.status_message_right, 0)

        self.connect_signals()

    def connect_signals(self):
        signals.new_statusbar_message.connect(self.left)
        signals.project_selected.connect(self.update_project)
        signals.database_selected.connect(self.set_database)

    def left(self, message):
        print(message)  # for console output
        if isinstance(message, str):
            self.status_message_left.setText(message)

    def center(self, message):
        self.status_message_center.setText(message)

    def right(self, message):
        self.status_message_right.setText(message)

    def update_project(self):
        name = projects.current
        self.center("Project: {}".format(name))
        self.right("Database: None")

    def set_database(self, name):
        self.right("Database: {}".format(name))
