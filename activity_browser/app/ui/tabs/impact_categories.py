# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from ..style import header
from ..tables import CFTable, MethodsTable
from ..panels import ABTab
from ...signals import signals


class CFsTab(QtWidgets.QWidget):
    def __init__(self, parent, method):
        super(CFsTab, self).__init__(parent)
        self.panel = parent
        self.method = method
        # Not visible when instantiated
        self.cf_table = CFTable()
        container = QtWidgets.QVBoxLayout()
        container.addWidget(header("Method: " + " - ".join(method)))
        container.addWidget(self.cf_table)
        container.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(container)

        self.cf_table.sync(method)
        self.cf_table.show()
        self.panel.select_tab(self)


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

        reset_search_button.clicked.connect(self.table.sync)
        reset_search_button.clicked.connect(self.search_box.clear)
        self.search_box.returnPressed.connect(lambda: self.table.sync(query=self.search_box.text()))
        signals.project_selected.connect(self.search_box.clear)


class CharacterizationFactorsTab(ABTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.tab_dict = {}
        signals.method_selected.connect(self.open_method_tab)
        signals.project_selected.connect(self.close_all)

    def open_method_tab(self, method):
        if method not in self.tab_dict:
            tab = CFsTab(self, method)
            full_tab_label = ' '.join(method)
            label = full_tab_label[:min((10, len(full_tab_label)))] + '..'
            self.tab_dict[method] = tab
            self.addTab(tab, label)
        else:
            tab = self.tab_dict[method]

        self.select_tab(tab)
        signals.method_tabs_changed.emit()

    def close_tab(self, index):
        tab = self.widget(index)
        del self.tab_dict[tab.method]
        self.removeTab(index)
        signals.method_tabs_changed.emit()

    def close_all(self):
        self.clear()
        self.tab_dict = {}
        signals.method_tabs_changed.emit()


