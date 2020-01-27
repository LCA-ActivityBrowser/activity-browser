# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from ..style import header, horizontal_line
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
        self.hide_uncertainty = QtWidgets.QCheckBox("Hide uncertainty columns")
        self.hide_uncertainty.setChecked(True)
        self.hide_uncertainty.toggled.connect(self.cf_table.hide_uncertain)
        toolbar = QtWidgets.QToolBar(self)
        toolbar.addWidget(self.hide_uncertainty)
        container = QtWidgets.QVBoxLayout()
        container.addWidget(header("Method: " + " - ".join(method)))
        container.addWidget(horizontal_line())
        container.addWidget(toolbar)
        container.addWidget(self.cf_table)
        container.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(container)

        self.cf_table.sync(method)
        self.cf_table.show()
        self.panel.select_tab(self)


class MethodsTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MethodsTab, self).__init__(parent)

        self.table = MethodsTable(self)
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter impact categories")
        reset_search_button = QtWidgets.QPushButton("Reset")
        #
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setAlignment(QtCore.Qt.AlignTop)
        search_layout.addWidget(header('Impact Categories'))
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
        self.table.new_method.connect(self.method_copied)

    @QtCore.Slot(tuple, name="searchCopiedMethod")
    def method_copied(self, method: tuple) -> None:
        """If a method is successfully copied, sync and filter for new name."""
        query = ", ".join(method)
        self.search_box.setText(query)
        self.table.sync(query)


class CharacterizationFactorsTab(ABTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)

        # signals
        signals.method_selected.connect(self.open_method_tab)
        self.tabCloseRequested.connect(self.close_tab)
        signals.project_selected.connect(self.close_all)

    def open_method_tab(self, method):
        if method not in self.tabs:
            new_tab = CFsTab(self, method)
            full_tab_label = ' '.join(method)
            label = full_tab_label[:min((10, len(full_tab_label)))] + '..'
            self.tabs[method] = new_tab
            self.addTab(new_tab, label)

        self.select_tab(self.tabs[method])
        signals.show_tab.emit("Characterization Factors")
