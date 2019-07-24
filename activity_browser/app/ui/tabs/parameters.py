# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot, QSize
from PyQt5.QtWidgets import (QHBoxLayout, QMessageBox, QPushButton, QToolBar,
                             QVBoxLayout)

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
        super().__init__(parent)

        self.project_table = ProjectParameterTable(self)
        self.database_table = DataBaseParameterTable(self)
        self.tables = {
            "project": self.project_table, "database": self.database_table
        }

        self.new_project_param = QPushButton(qicons.add, "New project parameter")
        self.save_project_btn = QPushButton(qicons.save_db, "Save project parameters")
        self.new_database_param = QPushButton(qicons.add, "New database parameter")
        self.save_database_btn = QPushButton(qicons.save_db, "Save database parameters")

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.

<h3>Formula field, in general:</h3>
The formula field is a string that is interpreted by brightway on save. Python builtin functions and Numpy functions
can be used within the formula!

<h3>Project</h3>
<ul>
<li>All project parameters must have a unique <em>name</em>.</li>
<li>The '<em>amount</em>' and '<em>formula</em>' fields are optional.</li>
<li>Project parameters can use other project parameters as part of a <em>formula</em>.</li>
</ul>

<h3>Database</h3>
<ul>
<li>All database parameters must have unique <em>name</em> within their database.</li>
<li>The '<em>amount</em>' and '<em>formula</em>' fields are optional.</li>
<li>Database parameters can use project and other database parameters as part of a <em>formula</em>.</li>
<li>If a project and database parameter use the same <em>name</em> and that <em>name</em> is used in
a <em>formula</em> of a second database parameter <em>within the same database</em>, the interpreter will
use the database parameter.</li>
</ul>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.new_project_param.clicked.connect(
            lambda: self.add_parameter("project")
        )
        self.new_database_param.clicked.connect(
            lambda: self.add_parameter("database")
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

        row = QToolBar()
        row.addWidget(header("Project- and Database parameters "))
        row.setIconSize(QSize(24, 24))
        row.addAction(
            qicons.question, "About project and database parameters",
            self.explanation
        )
        add_objects_to_layout(layout, row, horizontal_line())

        row = QHBoxLayout()
        add_objects_to_layout(
            row, header("Project parameters:"), self.new_project_param,
            self.save_project_btn
        )
        row.addStretch(1)
        add_objects_to_layout(layout, row, self.project_table)

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
    def add_parameter(self, name: str) -> None:
        """ Generic method for adding a single parameter to the given table
        """
        table = self.tables.get(name, None)
        if not table:
            return
        table.add_parameter()

    @pyqtSlot(str)
    def store_parameters(self, name: str) -> None:
        """ Store new / edited data, include handling for exceptions
        """
        table = self.tables.get(name, None)
        if not table:
            return

        error = table.save_parameters()
        if not error:
            table.sync(table.build_parameter_df())
            return
        elif error == QMessageBox.Discard:
            # Tables are rebuilt and ALL changes are reverted
            self.build_dataframes()
        elif error == QMessageBox.Cancel:
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
        super().__init__(parent)

        self.save_activities_btn = QPushButton(qicons.save_db, "Save activity parameters")
        self.save_exchanges_btn = QPushButton(qicons.save_db, "Save exchange parameters")
        self.act_table = ActivityParameterTable(self)
        self.exc_table = ExchangeParameterTable(self)
        self.tables = {
            "activity": self.act_table, "exchange": self.exc_table,
        }

        self._construct_layout()
        self._connect_signals()

        # To hold variable names that can be used in the formula
        self.variable_df = None

        self.explain_text = """
Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.

<h3>Activities</h3>
Activities can be dragged from a database in the left panel into the activity parameter table.
Dropping one or more activities into the table creates <em>temporary</em> parameters, only after
successfully saving the parameters is it possible to parameterize related exchanges.
<ul>
<li>Only the <em>group</em>, <em>name</em>, <em>amount</em> and <em>formula</em> fields are editable.</li>
<li>Only activities from editable databases can be parameterized.</li>
<li>The parameter <em>name</em> is unique per <em>group</em>.</li>
<li>The <em>amount</em> and <em>formula</em> fields are optional.</li>
</ul>

<h3>Exchanges</h3>
Exchanges can be parameterized by selecting one or more activity parameter and using
'Load all exchanges' in the context menu, this loads all of the exchanges of the selected
activities as <em>temporary</em> parameters. After setting a <em>formula</em> on any exchange,
the changes can be stored by saving. After saving, any temporary parameters without a
<em>formula</em> are cleared from the table.
<ul>
<li>Only the <em>formula</em> field is editable.</li>
<li>As with activities, only exchanges from editable databases can be parameterized.</li>
<li>The first time a <em>formula</em> is set on an exchange, its original <em>amount</em> is stored.
When a <em>formula</em> is removed from an exchange, an attempt is made to restore the original
amount.</li>
</ul>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_dataframes)
        self.save_activities_btn.clicked.connect(
            lambda: self.store_parameters("activity")
        )
        self.save_exchanges_btn.clicked.connect(
            lambda: self.store_parameters("exchange")
        )

    def _construct_layout(self):
        """ Construct the widget layout for the exchanges parameters tab
        """
        layout = QVBoxLayout()
        row = QToolBar()
        row.addWidget(header("Activity- and Exchange parameters "))
        row.setIconSize(QSize(24, 24))
        row.addAction(
            qicons.question, "About activity and exchange parameters",
            self.explanation
        )

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
            layout, row, horizontal_line(), act_row, self.act_table,
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
        self.exc_table.extend_exchange_df(key)

    @pyqtSlot()
    def reload_exchanges(self) -> None:
        """ Triggered from the activities table, reload the exchanges table
        """
        self.exc_table.sync(ExchangeParameterTable.build_parameter_df())

    @pyqtSlot(str)
    def store_parameters(self, name: str) -> None:
        """ Store new / edited data, include handling for exceptions
        """
        table = self.tables.get(name, None)
        if not table:
            return

        error = table.save_parameters()
        if not error:
            table.sync(table.build_parameter_df())
            return
        elif error == QMessageBox.Discard:
            # Tables are rebuilt and ALL changes are reverted
            self.build_dataframes()
        elif error == QMessageBox.Cancel:
            # Nothing is done, errors remain, tables are not rebuilt
            return
