# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from ..style import header
from ..icons import icons
from ..tables import (
    ActivitiesTable,
    DatabasesTable,
    BiosphereFlowsTable,
    ProjectListWidget,
)
from ...signals import signals


class ProjectTab(QtWidgets.QWidget):
    # TODO: Inventory is not the right name... It is really something like a "manager"
    def __init__(self, parent):
        super(ProjectTab, self).__init__(parent)
        # main widgets
        self.projects_widget = ProjectsWidget()
        self.databases_widget = DatabaseWidget(self)
        self.activities_widget = ActivitiesWidget(self)
        self.flows_widget = BiosphereFlowsWidget(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        # self.splitter.addWidget(self.projects_widget)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activities_widget)
        self.splitter.addWidget(self.flows_widget)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)

        # self.overall_layout.addWidget(self.databases_widget)
        # self.overall_layout.addWidget(self.activities_widget)
        # self.overall_layout.addWidget(self.flows_widget)
        self.overall_layout.addWidget(self.splitter)
        self.overall_layout.addStretch()
        self.setLayout(self.overall_layout)

        self.activities_widget.hide()
        self.flows_widget.hide()

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.activities_widget.table.setRowCount(0)
        self.flows_widget.table.setRowCount(0)
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_databases = self.databases_widget.table.rowCount() == 0
        no_activities = self.activities_widget.table.rowCount() == 0
        no_biosphere_flows = self.flows_widget.table.rowCount() == 0

        self.databases_widget.update_widget()

        if not no_databases and no_activities and no_biosphere_flows:
            self.databases_widget.label_no_database_selected.show()
        else:
            self.databases_widget.label_no_database_selected.hide()
        if no_activities:
            self.activities_widget.hide()
        else:
            self.activities_widget.show()
        if no_biosphere_flows:
            self.flows_widget.hide()
        else:
            self.flows_widget.show()
        self.resize_splitter()

    def resize_splitter(self):
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.databases_widget, self.activities_widget, self.flows_widget]
        sizes = [x.sizeHint().height() for x in widgets]
        self.splitter.setSizes(sizes)
        # print("Widget sizes:", sizes)
        # print("\nSH DB/Act/Bio: {}/{}/{}". format(*[x.sizeHint() for x in widgets]))
        # print("Splitter Sizes:", self.splitter.sizes())
        # print("SH Splitter Height:", self.splitter.height())


class ProjectsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ProjectsWidget, self).__init__()
        self.projects_list = ProjectListWidget()
        # Buttons
        self.new_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.copy), 'Copy current')
        self.delete_project_button = QtWidgets.QPushButton(
            QtGui.QIcon(icons.delete), 'Delete current'
        )
        # Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(header('Project:'))
        self.h_layout.addWidget(self.projects_list)
        self.h_layout.addWidget(self.new_project_button)
        self.h_layout.addWidget(self.copy_project_button)
        self.h_layout.addWidget(self.delete_project_button)
        self.setLayout(self.h_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum)
        )
        self.connect_signals()

    def connect_signals(self):
        self.new_project_button.clicked.connect(signals.new_project.emit)
        self.delete_project_button.clicked.connect(signals.delete_project.emit)
        self.copy_project_button.clicked.connect(signals.copy_project.emit)


class HeaderTableTemplate(QtWidgets.QWidget):
    searchable = False

    def __init__(self, parent):
        super(HeaderTableTemplate, self).__init__(parent)
        self.table = self.TABLE()

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.addWidget(header(self.HEADER))
        self.header_widget.setLayout(self.header_layout)

        if hasattr(self.table, "database_name"):
            self.label_database = QtWidgets.QLabel("[]")
            self.header_layout.addWidget(self.label_database)
            signals.database_selected.connect(self.database_changed)

        if self.searchable:  # include searchbox
            self.search_box = QtWidgets.QLineEdit()
            self.search_box.setPlaceholderText("Filter by search string")
            reset_search_button = QtWidgets.QPushButton("Reset")
            reset_search_button.clicked.connect(self.table.reset_search)
            reset_search_button.clicked.connect(self.search_box.clear)
            self.search_box.returnPressed.connect(self.set_search_term)
            self.fuzzy_checkbox = QtWidgets.QCheckBox('Fuzzy Search')
            self.fuzzy_checkbox.setToolTip(
                '''Try the fuzzy search if normal search doesn't yield the desired results.
                The fuzzy search currently only searches for matches in the  name field.'''
            )
            signals.project_selected.connect(self.search_box.clear)
            self.header_layout.addWidget(self.search_box)
            self.header_layout.addWidget(reset_search_button)
            self.header_layout.addWidget(self.fuzzy_checkbox)

        # Overall Layout
        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.v_layout.addWidget(self.header_widget)
        self.v_layout.addWidget(self.table)
        self.setLayout(self.v_layout)

        # Size Policy
        # self.header_widget.setSizePolicy(QtWidgets.QSizePolicy(
        #     QtWidgets.QSizePolicy.Maximum,
        #     QtWidgets.QSizePolicy.Maximum)
        # )
        self.table.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def set_search_term(self):
        search_term = self.search_box.text()
        if self.fuzzy_checkbox.isChecked() and hasattr(self.table, 'fuzzy_search_index'):
            self.table.update_search_index()
            self.table.fuzzy_search(search_term)
        else:
            self.table.search(search_term)

    def database_changed(self):
        if hasattr(self, "label_database"):
            self.label_database.setText("[{}]".format(self.table.database_name))


class DatabaseWidget(HeaderTableTemplate):
    TABLE = DatabasesTable
    HEADER = 'Databases:'

    def __init__(self, parent):
        super(DatabaseWidget, self).__init__(parent)

        # Labels
        self.label_no_database_selected = QtWidgets.QLabel(
            "Select a database (double-click on table)."
        )

        # Buttons
        self.add_default_data_button = QtWidgets.QPushButton(
            'Add Default Data (Biosphere flows, LCIA methods)')
        self.new_database_button = QtWidgets.QPushButton('New Database')
        self.import_database_button = QtWidgets.QPushButton('Import Database')

        # Header widget
        self.header_layout.addWidget(self.add_default_data_button)
        self.header_layout.addWidget(self.new_database_button)
        self.header_layout.addWidget(self.import_database_button)

        # Overall Layout
        self.v_layout.addWidget(self.label_no_database_selected)

        self.connect_signals()

    def connect_signals(self):
        self.add_default_data_button.clicked.connect(signals.install_default_data.emit)
        self.import_database_button.clicked.connect(signals.import_database.emit)
        self.new_database_button.clicked.connect(signals.add_database.emit)

    def update_widget(self):
        no_databases = self.table.rowCount() == 0
        if no_databases:
            self.add_default_data_button.show()
            self.import_database_button.hide()
            self.new_database_button.hide()
            self.table.hide()
            self.label_no_database_selected.hide()
        else:
            self.add_default_data_button.hide()
            self.import_database_button.show()
            self.new_database_button.show()
            self.table.show()


class ActivitiesWidget(HeaderTableTemplate):
    TABLE = ActivitiesTable
    HEADER = 'Activities:'
    searchable = True


class BiosphereFlowsWidget(HeaderTableTemplate):
    TABLE = BiosphereFlowsTable
    HEADER = 'Biosphere Flows:'
    searchable = True
