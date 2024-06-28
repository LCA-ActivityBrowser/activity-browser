from PySide2 import QtCore, QtWidgets

from activity_browser import signals
from activity_browser.mod import bw2data as bd

from ...ui.icons import qicons
from ...ui.style import header, horizontal_line
from ...ui.tables import (MethodCharacterizationFactorsTable, MethodsTable,
                          MethodsTree)
from ..panels import ABTab


class MethodCharacterizationFactorsTab(QtWidgets.QWidget):
    def __init__(self, parent, method_tuple):
        super().__init__(parent)
        self.panel = parent
        # Not visible when instantiated
        self.cf_table = MethodCharacterizationFactorsTable(self)
        self.cf_read_only_changed(False)  # don't accept drops, don't allow editing.
        self.hide_uncertainty = QtWidgets.QCheckBox("Hide uncertainty columns")
        self.hide_uncertainty.setChecked(True)
        self.read_only = True
        self.editable = QtWidgets.QCheckBox("Edit Characterization Factors")
        self.editable.setToolTip(
            "Make this impact category editable.\n"
            "Please make a duplicate of this CF before modifying it."
        )
        self.editable.toggled.connect(self.cf_read_only_changed)
        toolbar = QtWidgets.QToolBar(self)
        toolbar.addWidget(self.hide_uncertainty)
        toolbar.addWidget(self.editable)
        container = QtWidgets.QVBoxLayout()
        container.addWidget(header("Method: " + " - ".join(method_tuple)))
        container.addWidget(horizontal_line())
        container.addWidget(toolbar)
        container.addWidget(self.cf_table)
        container.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(container)

        self.method = bd.Method(method_tuple)
        self.cf_table.model.load(self.method)
        self.cf_table.show()
        self.panel.select_tab(self)

        self.connect_signals()

    def connect_signals(self) -> None:
        self.method.deleted.connect(self.deleteLater)
        self.hide_uncertainty.toggled.connect(self.cf_table.hide_uncertain)
        self.cf_table.model.updated.connect(self.cf_uncertain_changed)

    def cf_uncertain_changed(self):
        self.cf_table.hide_uncertain(self.hide_uncertainty.isChecked())
        self.cf_read_only_changed(self.editable.isChecked())

    def cf_read_only_changed(self, editable: bool) -> None:
        """When read_only=False specific data fields in the tables below become user-editable
        When read_only=True these same fields become read-only"""
        self.cf_table.read_only = self.read_only = not editable
        self.cf_table.setAcceptDrops(
            editable
        )  # also re-evaluated when dragging something over the table
        if editable:
            self.cf_table.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
        else:
            self.cf_table.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)


class MethodsTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MethodsTab, self).__init__(parent)

        self.tree = MethodsTree(self)
        self.tree.setToolTip(
            "Drag (groups of) impact categories to the calculation setup"
        )
        self.table = MethodsTable(self)
        self.table.setToolTip(
            "Drag (groups of) impact categories to the calculation setup"
        )

        # auto-search
        self.debounce_search = QtCore.QTimer()
        self.debounce_search.setInterval(300)
        self.debounce_search.setSingleShot(True)
        self.debounce_search.timeout.connect(self.set_search_term)

        #
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search impact categories")
        self.search_box.setToolTip(
            "If a large number of matches is found the\n"
            "tree is not expanded automatically."
        )
        self.search_button = QtWidgets.QToolButton()
        self.search_button.setIcon(qicons.search)
        self.search_button.setToolTip(
            "Search impact categories.\n"
            "If a large number of matches is found the\n"
            "tree is not expanded automatically."
        )
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
            "You can drag entire 'branches' of impact categories at once"
        )
        #
        self.mode_radio_list = QtWidgets.QRadioButton("List view")
        self.mode_radio_list.setToolTip("List view of impact categories")
        #
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_search_button)
        #
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.setAlignment(QtCore.Qt.AlignTop)
        mode_layout.addWidget(header("Impact Categories"))
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
        container.addWidget(self.tree)
        container.addWidget(self.table)
        self.table.setVisible(False)
        self.setLayout(container)

        self.connect_signals()

    def connect_signals(self):
        self.mode_radio_list.toggled.connect(self.update_view)

        self.reset_search_button.clicked.connect(self.table.sync)
        self.reset_search_button.clicked.connect(self.tree.model.sync)

        self.search_button.clicked.connect(self.set_search_term)
        self.search_button.clicked.connect(self.set_search_term)
        self.search_box.returnPressed.connect(self.set_search_term)
        self.search_box.returnPressed.connect(self.set_search_term)
        self.search_box.textChanged.connect(self.debounce_search.start)

        self.reset_search_button.clicked.connect(self.search_box.clear)
        bd.projects.current_changed.connect(self.search_box.clear)

    @QtCore.Slot(bool, name="isListToggled")
    def update_view(self, toggled: bool):
        self.tree.setVisible(not toggled)
        self.table.setVisible(toggled)

    def set_search_term(self):
        search_term = self.search_box.text().strip()
        self.table.sync(query=search_term)
        self.tree.model.sync(query=search_term)


class CharacterizationFactorsTab(ABTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)

        # signals
        signals.method_selected.connect(self.open_method_tab)
        self.tabCloseRequested.connect(self.close_tab)
        bd.projects.current_changed.connect(self.close_all)

    def open_method_tab(self, method):
        if method not in self.tabs:
            new_tab = MethodCharacterizationFactorsTab(self, method)
            full_tab_label = " ".join(method)
            label = full_tab_label[: min((10, len(full_tab_label)))] + ".."
            self.tabs[method] = new_tab

            new_tab.destroyed.connect(lambda: self.tabs.pop(method, None))
            new_tab.destroyed.connect(signals.hide_when_empty.emit)

            index = self.addTab(new_tab, label)
            self.setTabToolTip(index, full_tab_label)

        self.select_tab(self.tabs[method])
        signals.show_tab.emit("Characterization Factors")
