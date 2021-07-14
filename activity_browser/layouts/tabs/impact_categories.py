# -*- coding: utf-8 -*-

from PySide2 import QtCore, QtWidgets
from ...ui.icons import qicons

from ...ui.style import header, horizontal_line
from ...ui.tables import CFTable, MethodsTable, MethodsTree
from ...signals import signals
from ..panels import ABTab


class CFsTab(QtWidgets.QWidget):
    def __init__(self, parent, method):
        super().__init__(parent)
        self.panel = parent
        # Not visible when instantiated
        self.cf_table = CFTable(self)
        self.hide_uncertainty = QtWidgets.QCheckBox("Hide uncertainty columns")
        self.hide_uncertainty.setChecked(True)
        toolbar = QtWidgets.QToolBar(self)
        toolbar.addWidget(self.hide_uncertainty)
        container = QtWidgets.QVBoxLayout()
        container.addWidget(header("Method: " + " - ".join(method)))
        container.addWidget(horizontal_line())
        container.addWidget(toolbar)
        container.addWidget(self.cf_table)
        container.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(container)

        self.cf_table.model.sync(method)
        self.cf_table.show()
        self.panel.select_tab(self)

        self.connect_signals()

    def connect_signals(self) -> None:
        self.hide_uncertainty.toggled.connect(self.cf_table.hide_uncertain)
        self.cf_table.model.updated.connect(
            lambda: self.cf_table.hide_uncertain(self.hide_uncertainty.isChecked())
        )


class MethodsTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MethodsTab, self).__init__(parent)

        self.tree = MethodsTree(self)
        self.tree.setToolTip(
            "Drag (groups of) impact categories to the calculation setup")
        self.table = MethodsTable(self)
        self.table.setToolTip(
            "Drag (groups of) impact categories to the calculation setup")
        #
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search impact categories")
        self.search_box.setToolTip("If a large number of matches is found the\n"
                                   "tree is not expanded automatically.")
        self.search_button = QtWidgets.QToolButton()
        self.search_button.setIcon(qicons.search)
        self.search_button.setToolTip("Search impact categories.\n"
                                      "If a large number of matches is found the\n"
                                      "tree is not expanded automatically.")
        self.reset_search_button = QtWidgets.QToolButton()
        self.reset_search_button.setIcon(qicons.delete)
        self.reset_search_button.setToolTip("Clear the search")
        #
        self.mode_radio_tree = QtWidgets.QRadioButton("Tree view")
        self.mode_radio_tree.setChecked(True)
        self.mode_radio_tree.setToolTip(
            "Tree view of impact categories\n"
            "v CML 2001\n"
            "    v climate change\n"
            "        CML 2001, climate change, GWP 100a\n"
            "        ...\n"
            "You can drag entire 'branches' of impact categories at once")
        #
        self.mode_radio_list = QtWidgets.QRadioButton("List view")
        self.mode_radio_list.setToolTip(
            "List view of impact categories")
        #
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_search_button)
        #
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.setAlignment(QtCore.Qt.AlignTop)
        mode_layout.addWidget(header('Impact Categories'))
        search_layout.addWidget(self.mode_radio_tree)
        search_layout.addWidget(self.mode_radio_list)
        #
        mode_layout_container = QtWidgets.QWidget()
        mode_layout_container.setLayout(mode_layout)
        #
        search_layout_container = QtWidgets.QWidget()
        search_layout_container.setLayout(search_layout)
        #
        container = QtWidgets.QVBoxLayout()
        container.setAlignment(QtCore.Qt.AlignTop)
        container.addWidget(mode_layout_container)
        container.addWidget(search_layout_container)
        # container.addWidget(horizontal_line())
        container.addWidget(self.tree)
        container.addWidget(self.table)
        self.table.setVisible(False)
        self.setLayout(container)

        self.reset_search_button.clicked.connect(self.table.sync)
        self.reset_search_button.clicked.connect(self.tree.model.sync)

        self.search_button.clicked.connect(lambda: self.table.sync(query=self.search_box.text()))
        self.search_button.clicked.connect(lambda: self.tree.model.sync(query=self.search_box.text()))
        self.reset_search_button.clicked.connect(self.search_box.clear)
        self.search_box.returnPressed.connect(lambda: self.table.sync(query=self.search_box.text()))
        self.search_box.returnPressed.connect(lambda: self.tree.model.sync(query=self.search_box.text()))

        signals.project_selected.connect(self.search_box.clear)
        signals.new_method.connect(self.method_copied)

        self.connect_signals()

    def connect_signals(self):
        self.mode_radio_list.toggled.connect(self.update_view)

    @QtCore.Slot(tuple, name="searchCopiedMethod")
    def method_copied(self, method: tuple) -> None:
        """If a method is successfully copied, sync and filter for new name."""
        query = ", ".join(method)
        self.search_box.setText(query)

    @QtCore.Slot(bool, name="isListToggled")
    def update_view(self, toggled: bool):
        self.tree.setVisible(not toggled)
        # self.tree_settings_layout_container.setVisible(not toggled)
        self.table.setVisible(toggled)


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
