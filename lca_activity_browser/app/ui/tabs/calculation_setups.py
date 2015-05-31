# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...calculation_setups import (
    CSActivityTableWidget,
    CSListWidget,
    CSMethodsTableWidget,
)
from .. import horizontal_line, header
from PyQt4 import QtCore, QtGui


class CalculationSetupTab(QtGui.QWidget):
    def __init__(self, parent):
        super(CalculationSetupTab, self).__init__(parent)

        self.activities_table = CSActivityTableWidget()
        self.methods_table = CSMethodsTableWidget()
        self.list_widget = CSListWidget()

        self.new_cs_button = QtGui.QPushButton('New calculation setup')
        self.rename_cs_button = QtGui.QPushButton('Rename this setup')
        self.delete_cs_button = QtGui.QPushButton('Delete this setup')

        name_row = QtGui.QHBoxLayout()
        name_row.addWidget(header('Calculation Setups:'))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.rename_cs_button)
        name_row.addWidget(self.delete_cs_button)

        container = QtGui.QVBoxLayout()
        container.addLayout(name_row)
        container.addWidget(horizontal_line())
        container.addWidget(header('Products and amounts:'))
        container.addWidget(self.activities_table)
        container.addWidget(horizontal_line())
        container.addWidget(header('LCIA Methods:'))
        container.addWidget(self.methods_table)

        self.setLayout(container)
