# -*- coding: utf-8 -*-
from bw2parameters.errors import ParameterError, ValidationError
from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout
from PyQt5.QtCore import pyqtSlot

from activity_browser.app.bwutils import commontasks as bc
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
        self.project_df = None
        self.project_table = None
        self.database_df = None
        self.database_table = None

        super().__init__(parent)

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.new_project_param.clicked.connect(self.add_project_parameter)
        self.new_database_param.clicked.connect(self.add_database_parameter)
        self.save_parameter_btn.clicked.connect(self.save_all_parameters)

    def _construct_layout(self):
        """ Construct the widget layout for the variable parameters tab
        """
        layout = QVBoxLayout()
        self.save_parameter_btn = QPushButton("Save all parameters")
        self.project_table = ProjectParameterTable(self)
        self.database_table = DataBaseParameterTable(self)

        row = QHBoxLayout()
        row.addWidget(self.save_parameter_btn)
        row.addStretch(1)
        add_objects_to_layout(
            layout, header("Project- and Database parameters"),
            horizontal_line(), row
        )

        self.new_project_param = QPushButton("New project parameter")
        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Project parameters:"), self.new_project_param,
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.project_table)

        self.new_database_param = QPushButton("New database parameter")
        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Database parameters:"), self.new_database_param,
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.database_table)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_dataframes(self):
        """ Read parameters from brightway and build dataframe tables
        """
        self.project_df = ProjectParameterTable.build_parameter_df()
        self.project_table.sync(self.project_df)
        self.database_df = DataBaseParameterTable.build_parameter_df()
        self.database_table.sync(self.database_df)

    def add_project_parameter(self):
        """ Add a new project parameter to the dataframe

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called
        """
        self.project_df = self.project_df.append(
            {"name": None, "amount": 0.0, "formula": ""},
            ignore_index=True
        )
        self.project_table.sync(self.project_df)

    def add_database_parameter(self):
        """ Add a new project parameter to the dataframe

        NOTE: Any new parameters are only stored in memory until
        `save_project_parameters` is called
        """
        self.database_df = self.database_df.append(
            {"database": None, "name": None, "amount": 0.0, "formula": ""},
            ignore_index=True
        )
        self.database_table.sync(self.database_df)

    def save_all_parameters(self):
        """ Stores both project and database parameters
        """
        try:
            if len(self.project_df.index) > 0:
                self.save_project_parameters()
            if len(self.database_df.index) > 0:
                self.save_database_parameters()
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

    def save_project_parameters(self):
        """ Attempts to store all of the parameters in the dataframe
        as new (or updated) brightway project parameters
        """
        parameters = self.project_df.to_dict(orient='records')
        bc.save_parameters(parameters, "project")

    def save_database_parameters(self):
        """ Separates the database parameters by db_name and attempts
        to save each chunk of parameters separately.
        """
        used_db_names = self.database_df["database"].unique()
        for db_name in used_db_names:
            parameters = self.database_df.loc[self.database_df["database"] == db_name].to_dict(orient="records")
            bc.save_parameters(parameters, "database", db_or_group=db_name)


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
        new_df = self.exc_table.build_activity_exchange_df(key)
        # Now update the existing dataframe, overwriting old values
        self.exc_df = self.exc_table.combine_exchange_tables(self.exc_df, new_df)
        self.exc_table.sync(self.exc_df)

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
