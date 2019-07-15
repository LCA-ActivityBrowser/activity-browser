# -*- coding: utf-8 -*-
from bw2data.parameters import ActivityParameter
from bw2parameters.errors import ParameterError, ValidationError
from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout
from PyQt5.QtCore import pyqtSlot

from activity_browser.app.signals import signals

from ..style import header, horizontal_line
from ..tables import (ActivityParameterTable, DataBaseParameterTable,
                      ExchangeParameterTable, ProjectParameterTable)
from ..widgets import add_objects_to_layout
from .base import BaseRightTab, BaseRightTabbedTab


class ParametersTab(BaseRightTabbedTab):
    """ Parameters tab in which user can define project-, database- and
    activity-level parameters for their system.

    Changing projects will trigger a reload of all parameters
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(False)

        # Initialize both parameter tabs
        self.tabs.update({
            "Variables": ProjectDatabaseTab(self),
            "Exchanges": ProcessExchangeTab(self),
        })
        for name, tab in self.tabs.items():
            self.addTab(tab, name)

        for tab in self.tabs.values():
            if hasattr(tab, 'build_dataframes'):
                tab.build_dataframes()

    def _connect_signals(self):
        pass


class ProjectDatabaseTab(BaseRightTab):
    """ Project and Database parameters tab.

    This tab shows two tables containing the project and database level
    parameters set for the project.

    The user can create new parameters at both levels and save new parameters
    or updates to old ones with a single button.
    Pressing the save button will cause brightway to validate the changes
    and a warning message will appear if an error occurs.
    """
    def __init__(self, parent=None):
        self.project_table = None
        self.database_table = None
        super().__init__(parent)

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.new_project_param.clicked.connect(
            self.project_table.add_parameter
        )
        self.new_database_param.clicked.connect(
            self.database_table.add_parameter
        )
        self.save_project_btn.clicked.connect(
            lambda: self.store_parameters("project")
        )
        self.save_database_btn.clicked.connect(
            lambda: self.store_parameters("database")
        )

    def _construct_layout(self):
        """ Construct the widget layout for the variable parameters tab
        """
        layout = QVBoxLayout()
        self.project_table = ProjectParameterTable(self)
        self.database_table = DataBaseParameterTable(self)

        add_objects_to_layout(
            layout, header("Project- and Database parameters"),
            horizontal_line()
        )

        self.new_project_param = QPushButton("New project parameter")
        self.save_project_btn = QPushButton("Save project parameters")
        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Project parameters:"), self.new_project_param,
            self.save_project_btn
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.project_table)

        self.new_database_param = QPushButton("New database parameter")
        self.save_database_btn = QPushButton("Save database parameters")
        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Database parameters:"), self.new_database_param,
            self.save_database_btn
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.database_table)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_dataframes(self):
        """ Read parameters from brightway and build dataframe tables
        """
        self.project_table.sync(ProjectParameterTable.build_parameter_df())
        self.database_table.sync(DataBaseParameterTable.build_parameter_df())

    @pyqtSlot(str)
    def store_parameters(self, param_type: str) -> None:
        """ Stores either project or database parameters
        """
        result = None
        if param_type == "project":
            result = self.project_table.save_parameters()
        elif param_type == "database":
            result = self.database_table.save_parameters()

        if result:
            choice = result.exec()
            if choice == QMessageBox.Discard:
                # Tables are rebuilt and all changes are reverted
                self.build_dataframes()
            if choice == QMessageBox.Cancel:
                # No data is stored, tables are not rebuilt
                return
        else:
            # No error occurred and parameters are stored
            # Rebuild tables with recalculated values
            self.build_dataframes()


class ProcessExchangeTab(BaseRightTab):
    """ Activity and exchange parameters tab.

    This tab shows two tables containing the activity parameters and
    related exchanges where parameters are set.

    Dragging and dropping an activity from the left panel (database) into
    the table will create 'temporary' rows containing all valid exchanges
    where a parameter can be set.
    After adding formulas to the relevant exchanges the user can click
    'Save', upon which the table will store those activities and exchanges
    with parameters (formulas) while removing the un-parameterized exchanges.
    Exceptions caused by failed validation will be caught and presented
    to the user in a messagebox.

    NOTE: Only activities from a database that is NOT read-only
    can be dropped into the table.
    """

    def __init__(self, parent=None):
        self.act_df = None
        self.act_table = None
        self.exc_df = None
        self.exc_table = None
        super().__init__(parent)
        # To hold variable names that can be used in the formula
        self.variable_df = None

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.save_parameter_btn.clicked.connect(self.save_all_parameters)

    def _construct_layout(self):
        layout = QVBoxLayout()
        self.save_parameter_btn = QPushButton("Save all parameters")
        self.act_table = ActivityParameterTable(self)
        self.exc_table = ExchangeParameterTable(self)

        row = QHBoxLayout()
        row.addWidget(self.save_parameter_btn)
        row.addStretch(1)
        add_objects_to_layout(
            layout, header("Activity- and Exchange parameters"),
            horizontal_line(), row
        )
        row = QHBoxLayout()
        row.addWidget(header("Activity Parameters:"))
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.act_table)
        row = QHBoxLayout()
        add_objects_to_layout(row, header("Exchange parameters:"))
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.exc_table)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_dataframes(self):
        """ Read parameters from brightway and build dataframe tables
        """
        self.act_df = ActivityParameterTable.build_parameter_df()
        self.act_table.sync(self.act_df)
        self.exc_df = ExchangeParameterTable.build_parameter_df()
        self.exc_table.sync(self.exc_df)

    @pyqtSlot(tuple)
    def add_exchanges_action(self, key: tuple):
        """ Catches emitted signals from the activity table, trigger update
        of the exchange table for each signal.
        """
        try:
            new_df = self.exc_table.build_activity_exchange_df(key)
            # Now update the existing dataframe, overwriting old values
            self.exc_df = self.exc_table.combine_exchange_tables(self.exc_df, new_df)
            self.exc_table.sync(self.exc_df)
        except ActivityParameter.DoesNotExist as e:
            QMessageBox().warning(
                self,
                "Data missing",
                "Cannot retrieve exchanges of unsaved activity parameters",
                QMessageBox.Ok,
                QMessageBox.Ok
            )

    def save_all_parameters(self):
        """ Stores both project and database parameters
        """
        try:
            if len(self.act_df.index) > 0:
                pass
            if len(self.exc_df.index) > 0:
                pass
        except (AssertionError, ParameterError, ValidationError) as e:
            errorbox = QMessageBox()
            errorbox.setText("An error occured while saving parameters")
            errorbox.setInformativeText(
                "Discard changes or cancel and continue editing?"
            )
            errorbox.setDetailedText(str(e))
            errorbox.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel)
            errorbox.setDefaultButton(QMessageBox.Cancel)
            choice = errorbox.exec()

        if 'choice' in locals():
            if choice == QMessageBox.Discard:
                # Tables are rebuilt and all changes are reverted
                self.build_dataframes()
            if choice == QMessageBox.Cancel:
                # No data is stored, tables are not rebuilt
                pass
        else:
            # No error occurred and parameters are stored
            # Rebuild tables with recalculated values
            self.build_dataframes()
