# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot, QSize
from PyQt5.QtWidgets import (QHBoxLayout, QMessageBox, QPushButton, QToolBar,
                             QVBoxLayout, QTabWidget)

from activity_browser.app.signals import signals

from ..icons import qicons
from ..style import header, horizontal_line
from ..tables import (ActivityParameterTable, DataBaseParameterTable,
                      ExchangesTable, ProjectParameterTable)
from .base import BaseRightTab


class ParametersTab(QTabWidget):
    """ Parameters tab in which user can define project-, database- and
    activity-level parameters for their system.

    Changing projects will trigger a reload of all parameters
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(False)

        # Initialize both parameter tabs
        self.tabs = {
            "Definitions": ParameterDefinitionTab(self),
            "Exchanges": ParameterExchangesTab(self),
        }
        for name, tab in self.tabs.items():
            self.addTab(tab, name)

        for tab in self.tabs.values():
            if hasattr(tab, 'build_tables'):
                tab.build_tables()

        self._connect_signals()

    def _connect_signals(self):
        signals.add_activity_parameter.connect(self.activity_parameter_added)

    @pyqtSlot()
    def activity_parameter_added(self) -> None:
        """ Selects the correct sub-tab to show and trigger a switch to
        the Parameters tab.
        """
        self.setCurrentIndex(self.indexOf(self.tabs["Definitions"]))
        signals.show_tab.emit("Parameters")


class ParameterDefinitionTab(BaseRightTab):
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
        self.activity_table = ActivityParameterTable(self)
        self.tables = {
            "project": self.project_table, "database": self.database_table,
            "activity": self.activity_table,
        }

        self.new_project_param = QPushButton(qicons.add, "New project parameter")
        self.save_project_btn = QPushButton(qicons.save_db, "Save project parameters")
        self.new_database_param = QPushButton(qicons.add, "New database parameter")
        self.save_database_btn = QPushButton(qicons.save_db, "Save database parameters")
        self.save_activity_btn = QPushButton(qicons.save_db, "Save activity parameters")

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.</p>
<p>Note that project, database and activity parameters can store 
<a href="https://docs.brightwaylca.org/intro.html#storing-uncertain-values">uncertain values</a>, but these are
completely optional.</p>

<h3>Formula field, in general:</h3>
<p>The formula field is a string that is interpreted by brightway on save. Python builtin functions and Numpy functions
can be used within the formula!</p>

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

<h3>Activities</h3>
<p>Activities can be dragged from a database in the left panel into the activity parameter table.
Dropping one or more activities into the table creates <em>temporary</em> parameters.</p>
<ul>
<li>Only the <em>group</em>, <em>name</em>, <em>amount</em> and <em>formula</em> fields are editable.</li>
<li>Only activities from editable databases can be parameterized.</li>
<li>An activity can only belong to a single <em>group</em>. Multiple parameters can be created for
the activity in that group.</li>
<li>The parameter <em>name</em> is unique per <em>group</em>.</li>
<li>The <em>amount</em> and <em>formula</em> fields are optional.</li>
</ul>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_tables)
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
        self.save_activity_btn.clicked.connect(
            lambda: self.store_parameters("activity")
        )

    def _construct_layout(self):
        """ Construct the widget layout for the variable parameters tab
        """
        layout = QVBoxLayout()

        row = QToolBar()
        row.addWidget(header("Project-, Database- and Activity parameters "))
        row.setIconSize(QSize(24, 24))
        row.addAction(
            qicons.question, "About brightway parameters",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())

        row = QHBoxLayout()
        row.addWidget(header("Project parameters:"))
        row.addWidget(self.new_project_param)
        row.addWidget(self.save_project_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.project_table)

        row = QHBoxLayout()
        row.addWidget(header("Database parameters:"))
        row.addWidget(self.new_database_param)
        row.addWidget(self.save_database_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.database_table)

        row = QHBoxLayout()
        row.addWidget(header("Activity parameters:"))
        row.addWidget(self.save_activity_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.activity_table)

        layout.addStretch(1)
        self.setLayout(layout)

    def build_tables(self):
        """ Read parameters from brightway and build dataframe tables
        """
        self.project_table.sync(ProjectParameterTable.build_df())
        self.database_table.sync(DataBaseParameterTable.build_df())
        self.activity_table.sync(ActivityParameterTable.build_df())

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
            table.sync(table.build_df())
            return
        elif error == QMessageBox.Discard:
            # Tables are rebuilt and ALL changes are reverted
            self.build_tables()
        elif error == QMessageBox.Cancel:
            # Nothing is done, errors remain, tables are not rebuilt
            return


class ParameterExchangesTab(BaseRightTab):
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

        self.recalculate_btn = QPushButton(qicons.switch, "Recalculate exchanges")
        self.table = ExchangesTable(self)

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.</p>

<p>Shown here is an overview of all the parameters set on the current project.</p>
<p>Altering the formulas on exchanges in an activity tab will automatically update them here.</p>
<p>Changing amounts and/or formulas on project-, database- or activity parameters will not
immediately update the exchange parameters. Use the 'Recalculate exchanges' button to update
the exchange parameters with the changes from the other parameters.</p>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_tables)
        signals.parameters_changed.connect(self.build_tables)
        self.recalculate_btn.clicked.connect(self.table.recalculate_exchanges)

    def _construct_layout(self):
        """ Construct the widget layout for the exchanges parameters tab
        """
        layout = QVBoxLayout()
        row = QToolBar()
        row.addWidget(header("Exchange parameters overview "))
        row.setIconSize(QSize(24, 24))
        row.addAction(
            qicons.question, "About parameters overview",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())

        row = QHBoxLayout()
        row.addWidget(self.recalculate_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.table, 2)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_tables(self) -> None:
        """ Read parameters from brightway and build tree tables
        """
        self.table.sync()
