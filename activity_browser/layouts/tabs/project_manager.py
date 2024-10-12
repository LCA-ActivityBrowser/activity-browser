from PySide6 import QtCore, QtWidgets

from activity_browser import actions, signals
from activity_browser.mod import bw2data as bd
from activity_browser.layouts.panels import ABTab

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
        self.projects_widget = ProjectsWidget(self)
        self.databases_widget = DatabaseWidget(self)
        self.activity_biosphere_tabs = ActivityBiosphereTabs(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activity_biosphere_tabs)
        self.splitter.moveSplitter(0, 1)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)
        self.overall_layout.addWidget(self.splitter)
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        bd.projects.current_changed.connect(self.change_project)
        bd.databases.metadata_changed.connect(self.update_widgets)

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

        self.construct_layout()

    def construct_layout(self):
        h_widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setAlignment(QtCore.Qt.AlignLeft)
        h_layout.addWidget(header("Project:"))
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

        # Buttons
        self.add_default_data_button = actions.DefaultInstall.get_QButton()
        self.new_database_button = actions.DatabaseNew.get_QButton()
        self.import_database_button = actions.DatabaseImport.get_QButton()

        self.setMinimumHeight(200)

        self._construct_layout()

        # Signals
        bd.databases.metadata_changed.connect(self.update_widget)
        bd.projects.current_changed.connect(self.update_widget)

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
        bd.projects.current_changed.connect(self.close_all)

        self.tabCloseRequested.connect(self.close_tab)
        signals.database_selected.connect(self.open_or_focus_tab)

    def open_or_focus_tab(self, db_name: str) -> None:
        """Put focus on tab, if not open yet, open it."""
        # create the tab if it doesn't exist yet
        if not self.tabs.get(db_name, False):
            widget = ActivityBiosphereWidget(parent=self, db_name=db_name)
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


class ActivityBiosphereWidget(QtWidgets.QWidget):
    def __init__(self, parent, db_name: str):
        super(ActivityBiosphereWidget, self).__init__(parent)
        self.database = bd.Database(db_name)
        self.table = ActivitiesBiosphereTable(self)
        self.tree = None

        self.database.changed.connect(self.database_changed)
        self.database.deleted.connect(self.deleteLater)

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
        self.search_active = False

        self.mode_radio_list = QtWidgets.QRadioButton("List view")
        self.mode_radio_list.setChecked(True)
        self.mode_radio_list.setToolTip("List view of the database")
        self.mode_radio_list.hide()
        self.mode_radio_tree = QtWidgets.QRadioButton("Tree view")
        self.mode_radio_tree.setToolTip("Tree view of the database")
        self.mode_radio_tree.hide()
        self.mode_radio_tree.toggled.connect(self.update_view)

        self.header_layout.addWidget(self.mode_radio_list)
        self.header_layout.addWidget(self.mode_radio_tree)

        # Overall Layout
        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.v_layout.addWidget(self.header_widget)
        self.v_layout.addWidget(self.table)
        self.setLayout(self.v_layout)

        # load data
        self.database_changed(self.database)

    def create_tree(self):
        self.tree = ActivitiesBiosphereTree(self, self.database.name)

        # check if search was active, if so, apply to tree
        if self.search_active:
            self.tree.search(self.search_active)

        self.v_layout.addWidget(self.tree)
        self.reset_search_button.clicked.connect(self.tree.reset_search)

    def connect_signals(self):
        self.mode_radio_tree.toggled.connect(self.update_view)

    def reset_widget(self):
        self.hide()
        self.table.model.clear()
        self.tree = None

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

        bd.projects.current_changed.connect(self.search_box.clear)
        self.header_layout.addWidget(self.search_box)
        self.header_layout.addWidget(self.search_button)
        self.header_layout.addWidget(self.reset_search_button)

    def set_search_term(self):
        search_term = self.search_box.text().strip()
        self.search_active = search_term
        self.table.search(search_term)
        if isinstance(self.tree, ActivitiesBiosphereTree):
            self.tree.search(search_term)

    def reset_search(self):
        self.search_active = False
        self.search_box.clear()

    @QtCore.Slot(bool, name="isListToggled")
    def update_view(self, toggled: bool):
        self.table.setVisible(not toggled)

        if not isinstance(self.tree, ActivitiesBiosphereTree):
            self.create_tree()
        self.tree.setVisible(toggled)

    def database_changed(self, database: bd.Database) -> None:
        if (
            database.name != self.database.name
        ):  # only update if the database changed is the one shown by this widget
            return

        self.table.model.sync(self.database.name, query=self.table.model.query)

        if (
            "ISIC rev.4 ecoinvent" in self.table.model._dataframe.columns
            and not isinstance(self.tree, ActivitiesBiosphereTree)
        ):
            # a treeview does not exist and should be able to navigate to

            # set the view to list and show the radio buttons
            self.mode_radio_list.setChecked(True)
            self.mode_radio_tree.setChecked(False)
            self.mode_radio_list.show()
            self.mode_radio_tree.show()
        elif "ISIC rev.4 ecoinvent" in self.table.model._dataframe.columns:
            # a treeview exists, update it
            self.tree.get_expand_state()
            self.tree.model.setup_and_sync()
            self.tree.set_expand_state()

            # make sure that the radio buttons are available
            self.mode_radio_list.show()
            self.mode_radio_tree.show()
        else:
            # a treeview does not need to be shown

            # delete the tree if it exists
            if self.tree:
                self.tree.hide()
                self.tree = None
            # set the view to list and hide radio buttons
            self.mode_radio_list.hide()
            self.mode_radio_tree.hide()
            self.table.show()
