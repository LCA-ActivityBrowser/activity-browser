# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from ...ui.style import header
from ...ui.icons import qicons
from ...ui.tables import (
    DatabasesTable,
    ProjectListWidget,
    ActivitiesBiosphereTable,
)
from ...signals import signals


class ProjectTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ProjectTab, self).__init__(parent)
        # main widgets
        self.projects_widget = ProjectsWidget()
        self.databases_widget = DatabaseWidget(self)
        self.activity_biosphere_widget = ActivityBiosphereWidget(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        # self.splitter.addWidget(self.projects_widget)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activity_biosphere_widget)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)
        self.overall_layout.addWidget(self.splitter)
        self.overall_layout.addStretch()
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected)."""
        no_databases = self.databases_widget.table.rowCount() == 0

        self.databases_widget.update_widget()

        if not no_databases:
            self.databases_widget.label_no_database_selected.show()
        else:
            self.databases_widget.label_no_database_selected.hide()
            self.activity_biosphere_widget.hide()
        self.resize_splitter()

    def resize_splitter(self):
        """Splitter sizes need to be reset (for some reason this is buggy if not done like this)"""
        widgets = [self.databases_widget, self.activity_biosphere_widget]
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
        self.new_project_button = QtWidgets.QPushButton(qicons.add, "New")
        self.copy_project_button = QtWidgets.QPushButton(qicons.copy, "Copy")
        self.delete_project_button = QtWidgets.QPushButton(
            qicons.delete, "Delete"
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


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = DatabasesTable()

        # Labels
        self.label_no_database_selected = QtWidgets.QLabel(
            "Select a database (double-click on table)."
        )
        # Temporary inclusion to explain things before checkbox is back
        self.label_change_readonly = QtWidgets.QLabel(
            "To change a database from read-only to editable and back," +
            " click on the checkbox in the table."
        )

        # Buttons
        self.add_default_data_button = QtWidgets.QPushButton(
            qicons.import_db, "Add default data (biosphere flows and impact categories)"
        )
        self.new_database_button = QtWidgets.QPushButton(qicons.add, "New")
        self.import_database_button = QtWidgets.QPushButton(qicons.import_db, "Import")

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        self.add_default_data_button.clicked.connect(signals.install_default_data.emit)
        self.import_database_button.clicked.connect(lambda: signals.import_database.emit(self))
        self.new_database_button.clicked.connect(signals.add_database.emit)

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Databases:"))
        header_layout.addWidget(self.add_default_data_button)
        header_layout.addWidget(self.new_database_button)
        header_layout.addWidget(self.import_database_button)
        header_layout.addWidget(self.label_no_database_selected)
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
        if no_databases:
            self.add_default_data_button.show()
            self.import_database_button.hide()
            self.new_database_button.hide()
            self.table.hide()
            self.label_no_database_selected.hide()
            self.label_change_readonly.hide()
        else:
            self.add_default_data_button.hide()
            self.import_database_button.show()
            self.new_database_button.show()
            self.table.show()
            self.label_change_readonly.show()


class ActivityBiosphereWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ActivityBiosphereWidget, self).__init__(parent)
        self.header = 'Activities'

        self.table = ActivitiesBiosphereTable(self)

        # Header widget
        self.header_widget = QtWidgets.QWidget()
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.header_layout.addWidget(header(self.header))
        self.header_widget.setLayout(self.header_layout)

        self.label_database = QtWidgets.QLabel("[]")
        self.header_layout.addWidget(self.label_database)
        signals.database_selected.connect(self.update_table)

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

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_widget)

    # def sizeHint(self):
    #     return self.table.sizeHint()

    def reset_widget(self):
        self.hide()
        self.table.reset_table()

    def setup_search(self):
        # 1st search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Filter by search string")
        self.search_box.returnPressed.connect(self.set_search_term)

        # 2nd search box
        self.search_box2 = QtWidgets.QLineEdit()
        self.search_box2.setPlaceholderText("Filter by search string")
        self.search_box2.returnPressed.connect(self.set_search_term)

        # search logic between both search fields
        self.logic_dropdown = QtWidgets.QComboBox()
        self.logic_dropdown.addItems(['AND', 'OR', 'AND NOT'])

        # reset search
        reset_search_button = QtWidgets.QPushButton("Reset")
        reset_search_button.clicked.connect(self.table.reset_search)
        reset_search_button.clicked.connect(self.search_box.clear)
        reset_search_button.clicked.connect(self.search_box2.clear)

        signals.project_selected.connect(self.search_box.clear)
        self.header_layout.addWidget(self.search_box)
        self.header_layout.addWidget(self.logic_dropdown)
        self.header_layout.addWidget(self.search_box2)

        self.header_layout.addWidget(reset_search_button)

    def update_table(self, db_name='biosphere3'):
        # print('Updateing database table: ', db_name)
        if self.table.database_name:
            self.show()
        if len(db_name) > 15:
            self.label_database.setToolTip(db_name)
            db_display_name = db_name[:12] + '...'
        else:
            db_display_name = db_name
            self.label_database.setToolTip('')
        self.label_database.setText("[{}]".format(db_display_name))
        self.table.sync(db_name=db_name)

    def set_search_term(self):
        search_term = self.search_box.text()
        search_term2 = self.search_box2.text()
        logic = self.logic_dropdown.currentText()
        self.table.search(search_term, search_term2, logic=logic)
