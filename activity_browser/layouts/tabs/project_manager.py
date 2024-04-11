# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from activity_browser import actions, signals, project_controller
from ..panels import ABTab
from ...ui.style import header
from ...ui.icons import qicons
from ...ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
)


class ProjectTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ProjectTab, self).__init__(parent)
        # main widgets
        self.projects_widget = ProjectsWidget()
        self.databases_widget = DatabaseWidget(self)
        self.activity_biosphere_tabs = ActivityBiosphereTabs(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activity_biosphere_tabs)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)
        self.overall_layout.addWidget(self.splitter)
        self.overall_layout.addStretch()
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        project_controller.project_switched.connect(self.change_project)
        signals.database_selected.connect(self.update_widgets)
        signals.database_changed.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_databases = len(self.activity_biosphere_tabs.tabs) == 0

        self.databases_widget.update_widget()

        self.activity_biosphere_tabs.setVisible(not no_databases)
        self.resize_splitter()

    def resize_splitter(self):
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.databases_widget, self.activity_biosphere_tabs]
        sizes = [x.sizeHint().height() for x in widgets]
        tabheight = self.height()
        if sum(sizes) > tabheight and sizes[1] > 0.75 * tabheight:
            sizes[0] = sizes[1] // 3
        self.splitter.setSizes(sizes)


class ProjectsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ProjectsWidget, self).__init__()
        self.projects_list = ProjectListWidget()

        # Buttons
        self.new_project_button = actions.ProjectNew(self).get_button()
        self.copy_project_button = actions.ProjectDuplicate(self).get_button()
        self.delete_project_button = actions.ProjectDelete(self).get_button()

        self.construct_layout()

    def construct_layout(self):
        h_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setAlignment(QtCore.Qt.AlignLeft)
        h_layout.addWidget(header('Project:'))
        h_layout.addWidget(self.projects_list)
        h_layout.addWidget(self.new_project_button)
        h_layout.addWidget(self.copy_project_button)
        h_layout.addWidget(self.delete_project_button)
        h_widget.setLayout(h_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(h_widget)
        self.setLayout(layout)

        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        )


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = DatabasesTable()
        self.table.setToolTip("To select a database, double-click on an entry")

        # Temporary inclusion to explain things before checkbox is back
        self.label_change_readonly = QtWidgets.QLabel(
            "To change a database from read-only to editable and back," +
            " click on the checkbox in the table."
        )

        # Buttons
        self.add_default_data_button = actions.DefaultInstall(self).get_button()
        self.new_database_button = actions.DatabaseNew(self).get_button()
        self.import_database_button = actions.DatabaseImport(self).get_button()

        self._construct_layout()

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Databases:"))
        header_layout.addWidget(self.add_default_data_button)
        header_layout.addWidget(self.new_database_button)
        header_layout.addWidget(self.import_database_button)
        header_widget.setLayout(header_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(self.label_change_readonly)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_widget(self):
        no_databases = self.table.rowCount() == 0
        self.add_default_data_button.setVisible(no_databases)
        self.import_database_button.setVisible(not no_databases)
        self.new_database_button.setVisible(not no_databases)

        self.table.setVisible(not no_databases)
        self.label_change_readonly.setVisible(not no_databases)


class ActivityBiosphereTabs(ABTab):
    def __init__(self, parent=None):
        super(ActivityBiosphereTabs, self).__init__(parent)
        self.setTabsClosable(True)

        self.connect_signals()

    def connect_signals(self) -> None:
        self.tabCloseRequested.connect(self.close_tab)
        signals.database_selected.connect(self.open_or_focus_tab)
        signals.database_changed.connect(self.update_activity_biosphere_widget)
        signals.delete_database_confirmed.connect(self.close_tab_by_tab_name)

        project_controller.project_switched.connect(self.close_all)

    def open_or_focus_tab(self, db_name: str) -> None:
        """Put focus on tab, if not open yet, open it.
        """
        # create the tab if it doesn't exist yet
        if not self.tabs.get(db_name, False):
            widget = ActivityBiosphereWidget(parent=self)
            self.add_tab(widget, db_name)
            self.update_activity_biosphere_widget(db_name)

        # put the focus on this tab + send signal that this is the open db
        self.select_tab(self.tabs[db_name])

    def current_index_changed(self, current_index: int) -> None:
        db_name = self.get_tab_name_from_index(current_index)
        signals.database_tab_open.emit(db_name)

    def update_activity_biosphere_widget(self, db_name: str) -> None:
        """Check if database is open, if so, update the underlying data"""
        if self.tabs.get(db_name, False):
            self.tabs[db_name].table.model.sync(db_name)


class ActivityBiosphereWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ActivityBiosphereWidget, self).__init__(parent)
        self.table = ActivitiesBiosphereTable(self)

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_widget.setLayout(self.header_layout)

        # auto-search
        self.debounce_search = QtCore.QTimer()
        self.debounce_search.setInterval(300)
        self.debounce_search.setSingleShot(True)
        self.debounce_search.timeout.connect(self.set_search_term)

        self.setup_search()

        # Overall Layout
        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.v_layout.addWidget(self.header_widget)
        self.v_layout.addWidget(self.table)
        self.setLayout(self.v_layout)

        self.table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def reset_widget(self):
        self.hide()
        self.table.model.clear()

    def setup_search(self):
        # 1st search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search")
        self.search_box.textChanged.connect(self.debounce_search.start)
        self.search_box.returnPressed.connect(self.set_search_term)

        # search
        self.search_button = QtWidgets.QToolButton()
        self.search_button.setIcon(qicons.search)
        self.search_button.setToolTip("Filter activities")
        self.search_button.clicked.connect(self.set_search_term)

        # reset search
        self.reset_search_button = QtWidgets.QToolButton()
        self.reset_search_button.setIcon(qicons.delete)
        self.reset_search_button.setToolTip("Clear the search")
        self.reset_search_button.clicked.connect(self.table.reset_search)
        self.reset_search_button.clicked.connect(self.search_box.clear)

        project_controller.project_switched.connect(self.search_box.clear)
        self.header_layout.addWidget(self.search_box)

        self.header_layout.addWidget(self.search_button)
        self.header_layout.addWidget(self.reset_search_button)

    def set_search_term(self):
        search_term = self.search_box.text().strip()
        self.table.search(search_term)
