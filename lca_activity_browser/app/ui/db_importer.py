# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets


class DatabaseImportDialog(QtWidgets.QWizardPage):
    def __init__(self):
        super().__init__()
        self.label = QtWidgets.QLabel('hello world')
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.show()
