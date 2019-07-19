# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout

from activity_browser.app.signals import signals

from ..icons import qicons
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
        self.save_project_btn.clicked.connect(self.store_project_parameters)
        self.save_database_btn.clicked.connect(self.store_database_parameters)

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

        self.new_project_param = QPushButton(qicons.add, "New project parameter")
        self.save_project_btn = QPushButton(qicons.save_db, "Save project parameters")
        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Project parameters:"), self.new_project_param,
            self.save_project_btn
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.project_table)

        self.new_database_param = QPushButton(qicons.add, "New database parameter")
        self.save_database_btn = QPushButton(qicons.save_db, "Save database parameters")
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

    @pyqtSlot()
    def store_project_parameters(self) -> None:
        """ Store project parameters
        """
        error = self.project_table.save_parameters()
        if not error:
            self.project_table.sync(ProjectParameterTable.build_parameter_df())
        else:
            self.handle_error(error)

    @pyqtSlot()
    def store_database_parameters(self) -> None:
        """ Store database parameters
        """
        error = self.database_table.save_parameters()
        if not error:
            self.database_table.sync(DataBaseParameterTable.build_parameter_df())
        else:
            self.handle_error(error)

    def handle_error(self, messagebox: QMessageBox) -> None:
        """ If saving parameters failed, allow user to determine next step
        """
        choice = messagebox.exec()
        if choice == QMessageBox.Discard:
            # Tables are rebuilt and ALL changes are reverted
            self.build_dataframes()
        if choice == QMessageBox.Cancel:
            # Nothing is done, errors remain, tables are not rebuilt
            return


class ProcessExchangeTab(BaseRightTab):
    """ Activity and exchange parameters tab.

    This tab shows two tables containing the activity parameters and
    related exchanges where parameters are set.

    Dragging and dropping an activity from the left panel (database) into
    the activity table will create a 'temporary' row containing the activity,
    adding a ground name and paramater name will allow the user to save
    the activity parameter.
    Once saved, the exchanges for that activity can be extracted through
    a context menu into the exchange table.
    After adding formulas to the relevant exchanges the user can click
    'Save', upon which the table will store those activities and exchanges
    with parameters (formulas) while removing the un-parameterized exchanges.
    Exceptions caused by failed validation will be caught and presented
    to the user in a messagebox.

    NOTE: Only activities from a database that is NOT read-only
    can be dropped into the table.
    """

    def __init__(self, parent=None):
        self.act_table = None
        self.exc_table = None
        super().__init__(parent)
        # To hold variable names that can be used in the formula
        self.variable_df = None

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.save_activities_btn.clicked.connect(self.store_activity_parameters)
        self.save_exchanges_btn.clicked.connect(self.store_exchange_parameters)

    def _construct_layout(self):
        layout = QVBoxLayout()
        self.save_activities_btn = QPushButton(qicons.save_db, "Save activity parameters")
        self.save_exchanges_btn = QPushButton(qicons.save_db, "Save exchange parameters")
        self.act_table = ActivityParameterTable(self)
        self.exc_table = ExchangeParameterTable(self)

        act_row = QHBoxLayout()
        add_objects_to_layout(
            act_row, header("Activity Parameters:"), self.save_activities_btn
        )
        act_row.addStretch(1)
        exc_row = QHBoxLayout()
        add_objects_to_layout(
            exc_row, header("Exchange parameters:"), self.save_exchanges_btn
        )
        exc_row.addStretch(1)
        add_objects_to_layout(
            layout, header("Activity- and Exchange parameters"),
            horizontal_line(), act_row, self.act_table,
            exc_row, self.exc_table
        )
        layout.addStretch(1)
        self.setLayout(layout)

    def build_dataframes(self) -> None:
        """ Read parameters from brightway and build dataframe tables
        """
        self.act_table.sync(ActivityParameterTable.build_parameter_df())
        self.exc_table.sync(ExchangeParameterTable.build_parameter_df())

    @pyqtSlot(tuple)
    def add_exchanges_action(self, key: tuple) -> None:
        """ Catches emitted signals from the activity table, trigger update
        of the exchange table for each signal.
        """
        result = self.exc_table.extend_exchange_df(key)
        if result:
            result.exec()

    @pyqtSlot()
    def reload_exchanges(self) -> None:
        """ Triggered from the activities table, reload the exchanges table
        """
        self.exc_table.sync(ExchangeParameterTable.build_parameter_df())

    @pyqtSlot()
    def store_activity_parameters(self) -> None:
        """ Store activity parameters
        """
        error = self.act_table.save_parameters()
        if not error:
            self.act_table.sync(ActivityParameterTable.build_parameter_df())
        else:
            self.handle_error(error)

    @pyqtSlot()
    def store_exchange_parameters(self) -> None:
        """ Store exchange parameters
        """
        error = self.exc_table.save_parameters()
        if not error:
            self.exc_table.sync(ExchangeParameterTable.build_parameter_df())
        else:
            self.handle_error(error)

    def handle_error(self, messagebox: QMessageBox) -> None:
        """ If saving parameters failed, allow user to determine next step
        """
        choice = messagebox.exec()
        if choice == QMessageBox.Discard:
            # Tables are rebuilt and ALL changes are reverted
            self.build_dataframes()
        if choice == QMessageBox.Cancel:
            # Nothing is done, errors remain, tables are not rebuilt
            return
