# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from ..style import horizontal_line, header
from ..tables import CFTable, MethodsTable
from ...signals import signals


class CFsTab(QtWidgets.QWidget):
    NO_METHOD = 'No method selected yet'

    def __init__(self, parent):
        super(CFsTab, self).__init__(parent)
        self.panel = parent
        # Not visible when instantiated
        self.cf_table = CFTable()
        self.no_method_label = QtWidgets.QLabel(self.NO_METHOD)
        container = QtWidgets.QVBoxLayout()
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


class MethodsTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MethodsTab, self).__init__(parent)

        self.table = MethodsTable()
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter LCIA methods")
        reset_search_button = QtWidgets.QPushButton("Reset")
        #
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setAlignment(QtCore.Qt.AlignTop)
        search_layout.addWidget(header('LCIA Methods:'))
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(reset_search_button)
        #
        search_layout_container = QtWidgets.QWidget()
        search_layout_container.setLayout(search_layout)
        #
        container = QtWidgets.QVBoxLayout()
        container.setAlignment(QtCore.Qt.AlignTop)
        container.addWidget(search_layout_container)
        # container.addWidget(horizontal_line())
        container.addWidget(self.table)
        self.setLayout(container)
        #
        # signals.project_selected.connect(lambda x: self.table.sync())
        # signals.project_selected.connect(self.table.sync)
        # # reset_search_button.clicked.connect(self.table.sync)
        # reset_search_button.clicked.connect(self.search_box.clear)
        # # self.search_box.returnPressed.connect(lambda: self.table.sync(query=self.search_box.text()))
        # signals.project_selected.connect(self.search_box.clear)

