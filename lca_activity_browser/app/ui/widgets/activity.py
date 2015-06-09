# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from PyQt4 import QtCore, QtGui


class ActivityDataGrid(QtGui.QWidget):
    def __init__(self, parent=None, activity=None):
        super(ActivityDataGrid, self).__init__(parent)
        self.activity = activity

        self.grid = self.get_grid()
        self.setLayout(self.grid)

        if activity:
            self.populate()

    def get_grid(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QtGui.QLabel('Name'), 1, 1)
        self.name_box = QtGui.QLineEdit()
        self.name_box.setPlaceholderText("Activity name")
        grid.addWidget(self.name_box, 1, 2, 1, 3)

        grid.addWidget(QtGui.QLabel('Comment'), 2, 1, 2, 1)
        self.comment_box = QtGui.QPlainTextEdit()
        grid.addWidget(self.comment_box, 2, 2, 2, 3)

        grid.addWidget(QtGui.QLabel('Location'), 3, 1)
        self.location_box = QtGui.QLineEdit()
        self.location_box.setPlaceholderText("ISO 2-letter code or custom name")
        grid.addWidget(self.location_box, 3, 2, 1, 3)

        grid.addWidget(QtGui.QLabel('Unit'), 4, 1)
        self.unit_box = QtGui.QLineEdit()
        grid.addWidget(self.unit_box, 4, 2, 1, 3)

        grid.setAlignment(QtCore.Qt.AlignTop)

        return grid

    def populate(self, activity=None):
        if activity:
            self.activity = activity
        self.name_box.setText(self.activity['name'])
        self.comment_box.setPlainText(self.activity.get('comment', ''))
        self.location_box.setText(self.activity.get('location', ''))
        self.unit_box.setText(self.activity.get('unit', ''))


ActivityDialog = None
