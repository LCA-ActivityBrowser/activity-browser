# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ..tables import CFsTableWidget, MethodsTableWidget
from ...signals import signals
from PyQt4 import QtCore, QtGui


class CFsTab(QtGui.QWidget):
    NO_METHOD = 'No method selected yet'

    def __init__(self, parent):
        super(CFsTab, self).__init__(parent)
        self.panel = parent
        # Not visible when instantiated
        self.cf_table = CFsTableWidget()
        self.no_method_label = QtGui.QLabel(self.NO_METHOD)
        container = QtGui.QVBoxLayout()
        container.addWidget(header('Characterization Factors:'))
        container.addWidget(horizontal_line())
        container.addWidget(self.no_method_label)
        container.addWidget(self.cf_table)
        container.setAlignment(QtCore.Qt.AlignTop)

        signals.project_selected.connect(self.hide_cfs_table)
        signals.method_selected.connect(self.add_cfs_table)

        self.setLayout(container)

    def add_cfs_table(self, method):
        self.no_method_label.setText(
            "Method: " + " - ".join(method)
        )
        self.cf_table.sync(method)
        self.cf_table.show()
        self.panel.select_tab(self)

    def hide_cfs_table(self):
        self.cf_table.hide()
        self.cf_table.clear()
        self.no_method_label.setText(self.NO_METHOD)


class MethodsTab(QtGui.QWidget):
    def __init__(self, parent):
        super(MethodsTab, self).__init__(parent)

        self.table = MethodsTableWidget()

        container = QtGui.QVBoxLayout()
        container.addWidget(header('LCIA Methods:'))
        container.addWidget(horizontal_line())
        container.addWidget(self.table)
        self.setLayout(container)

        signals.project_selected.connect(self.flush_table)

    def flush_table(self, name):
        self.table.sync()
