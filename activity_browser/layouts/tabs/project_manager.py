from qtpy import QtCore, QtWidgets

from activity_browser import actions, signals
from activity_browser.mod import bw2data as bd
from activity_browser.layouts.panels import ABTab
from activity_browser.layouts import panes

from ...ui.style import header
from ...ui.icons import qicons
from ...ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
    ActivitiesBiosphereTree,
)


class ProjectTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ProjectTab, self).__init__(parent)
        # main widgets
        self.databases_widget = panes.Databases(self)
        self.activity_biosphere_tabs = ActivityBiosphereTabs(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activity_biosphere_tabs)
        self.splitter.moveSplitter(0, 1)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.splitter)
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.change_project)
        signals.meta.databases_changed.connect(self.update_widgets)

        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected).
        """
        no_databases = len(self.activity_biosphere_tabs.tabs) == 0

        self.activity_biosphere_tabs.setVisible(not no_databases)


class ProjectsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ProjectsWidget, self).__init__(parent)
        self.projects_list = ProjectListWidget()

        # Buttons
        self.new_project_button = actions.ProjectNew.get_QButton()
        self.copy_project_button = actions.ProjectDuplicate.get_QButton()
        self.delete_project_button = actions.ProjectDelete.get_QButton()
        self.remote_import_project_button = actions.ProjectRemoteImport.get_QButton()
        self.local_import_project_button = actions.ProjectLocalImport.get_QButton()

        self.construct_layout()

    def construct_layout(self):
        project_list_widget = QtWidgets.QWidget()
        project_list_layout = QtWidgets.QHBoxLayout()
        project_list_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_list_layout.addWidget(header("Project:"))
        project_list_layout.addWidget(self.projects_list)
        project_list_widget.setLayout(project_list_layout)

        project_actions_widget = QtWidgets.QWidget()
        project_actions_layout = QtWidgets.QVBoxLayout()
        project_create_delete_layout = QtWidgets.QHBoxLayout()
        project_create_delete_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_create_delete_layout.addWidget(self.new_project_button)
        project_create_delete_layout.addWidget(self.copy_project_button)
        project_create_delete_layout.addWidget(self.delete_project_button)
        project_actions_layout.addLayout(project_create_delete_layout)
        project_import_layout = QtWidgets.QHBoxLayout()
        project_import_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_import_layout.addWidget(self.remote_import_project_button)
        project_import_layout.addWidget(self.local_import_project_button)
        project_actions_layout.addLayout(project_import_layout)
        project_actions_widget.setLayout(project_actions_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(project_list_widget)
        layout.addWidget(project_actions_widget)
        self.setLayout(layout)

        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum
            )
        )


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = DatabasesTable()
        self.table.setToolTip("To select a database, double-click on an entry")

        # Temporary inclusion to explain things before checkbox is back
        self.label_change_readonly = QtWidgets.QLabel(
            "To change a database from read-only to editable and back,"
            + " click on the checkbox in the table."
        )
        self.label_change_readonly.setWordWrap(True)

        # Buttons
        self.add_default_data_button = actions.DefaultInstall.get_QButton()
        self.new_database_button = actions.DatabaseNew.get_QButton()
        self.import_database_button = actions.DatabaseImport.get_QButton()

        self.setMinimumHeight(200)

        self._construct_layout()

        # Signals
        signals.meta.databases_changed.connect(self.update_widget)
        signals.project.changed.connect(self.update_widget)

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
        signals.project.changed.connect(self.close_all)

        self.tabCloseRequested.connect(self.close_tab)
        signals.database_selected.connect(self.open_or_focus_tab)

    def open_or_focus_tab(self, db_name: str) -> None:
        """Put focus on tab, if not open yet, open it."""
        # create the tab if it doesn't exist yet
        if not self.tabs.get(db_name, False):
            widget = panes.DatabaseFunctions(parent=self, db_name=db_name)
            self.add_tab(widget, db_name)

            widget.destroyed.connect(
                lambda: self.tabs.pop(db_name) if db_name in self.tabs else None
            )

        # put the focus on this tab + send signal that this is the open db
        self.select_tab(self.tabs[db_name])

    def current_index_changed(self, current_index: int) -> None:
        if current_index < 0:
            self.hide()
            return
        db_name = self.get_tab_name_from_index(current_index)
        signals.database_tab_open.emit(db_name)

