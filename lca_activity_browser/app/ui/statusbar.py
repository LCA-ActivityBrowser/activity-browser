# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from ..signals import signals


class Statusbar(object):
    def __init__(self, window):
        self.window = window
        self.statusbar = QtWidgets.QStatusBar()
        self.window.setStatusBar(self.statusbar)

        self.status_message_left = QtWidgets.QLabel('Welcome')
        self.status_message_right = QtWidgets.QLabel('Database')
        self.status_message_center = QtWidgets.QLabel('Project: Default')

        self.statusbar.addWidget(self.status_message_left, 1)
        self.statusbar.addWidget(self.status_message_center, 2)
        self.statusbar.addWidget(self.status_message_right, 0)

        signals.project_selected.connect(self.set_project)
        signals.database_selected.connect(self.set_database)

    def left(self, message):
        self.status_message_left.setText(message)

    def center(self, message):
        self.status_message_center.setText(message)

    def right(self, message):
        self.status_message_right.setText(message)

    def set_project(self, name):
        self.center("Project: {}".format(name))
        self.right("Database: None")

    def set_database(self, name):
        self.right("Database: {}".format(name))
