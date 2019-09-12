# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot, QSize
from PyQt5.QtWidgets import (QCheckBox, QHBoxLayout, QMessageBox, QPushButton,
                             QToolBar, QVBoxLayout, QTabWidget)

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
        # signals.add_activity_parameter.connect(self.activity_parameter_added)
        pass

    @pyqtSlot()
    def activity_parameter_added(self) -> None:
        """ Selects the correct sub-tab to show and trigger a switch to
        the Parameters tab.
        """
        self.setCurrentIndex(self.indexOf(self.tabs["Definitions"]))
        signals.show_tab.emit("Parameters")


class ParameterDefinitionTab(BaseRightTab):
    """ Parameter definitions tab.

    This tab shows three tables containing the project-, database- and
    activity level parameters set for the project.

    The user can create new parameters at these three levels and save
    new or edited parameters with a single button.
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
        self.save_project_btn = QPushButton(qicons.save_db, "Store new parameters")
        self.save_project_btn.setEnabled(False)
        self.new_database_param = QPushButton(qicons.add, "New database parameter")
        self.save_database_btn = QPushButton(qicons.save_db, "Store new parameters")
        self.save_database_btn.setEnabled(False)
        self.save_activity_btn = QPushButton(qicons.save_db, "Store new parameters")
        self.save_activity_btn.setEnabled(False)
        self.show_order = QCheckBox("Show order column", self)
        self.uncertainty_columns = QCheckBox("Show uncertainty columns", self)
        self.buttons = {
            "project": self.save_project_btn, "database": self.save_database_btn,
            "activity": self.save_activity_btn,
        }

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.</p>
<p>Note that project, database and activity parameters can store 
<a href="https://docs.brightwaylca.org/intro.html#storing-uncertain-values">uncertain values</a>, but these are
completely optional.</p>

<h3>In general:</h3>
<p>Any errors that occur when saving new/edited parameters are presented as clearly as possible. In most cases
problems can be resolved by checking that the <em>name</em>, <em>database</em> or <em>group</em> fields
are filled out.</p>
<p>The formula field is a string that is interpreted by brightway on save. Python builtin functions and Numpy functions
can be used within the formula!</p>

<h3>Project</h3>
<p> New parameters added by the relevant button are temporary until stored.</p>
<ul>
<li>All project parameters must have a unique <em>name</em>.</li>
<li>The '<em>amount</em>' and '<em>formula</em>' fields are optional.</li>
<li>Project parameters can use other project parameters as part of a <em>formula</em>.</li>
</ul>

<h3>Database</h3>
<p> New parameters added by the relevant button are temporary until stored.</p>
<ul>
<li>All database parameters must have unique <em>name</em> within their database.</li>
<li>The '<em>amount</em>' and '<em>formula</em>' fields are optional.</li>
<li>Database parameters can use project and other database parameters as part of a <em>formula</em>.</li>
<li>If a project and database parameter use the same <em>name</em> and that <em>name</em> is used in
a <em>formula</em> of a second database parameter <em>within the same database</em>, the interpreter will
use the database parameter.</li>
</ul>

<h3>Activities</h3>
<p>New parameters are added either by drag-and-dropping from the database table or by clicking
the <em>parameterize</em> button within an Activity tab. Whatever the case, the newly added
parameters are 'temporary' to allow the user to change the default <em>group</em> and
<em>name</em> values.</p>
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
        signals.parameters_changed.connect(self.build_tables)
        self.new_project_param.clicked.connect(
            self.project_table.add_parameter
        )
        self.new_database_param.clicked.connect(
            self.database_table.add_parameter
        )
        self.save_project_btn.clicked.connect(
            lambda: self.store_parameters("project")
        )
        self.project_table.new_parameter.connect(
            lambda: self.save_project_btn.setEnabled(True)
        )
        self.save_database_btn.clicked.connect(
            lambda: self.store_parameters("database")
        )
        self.database_table.new_parameter.connect(
            lambda: self.save_database_btn.setEnabled(True)
        )
        self.save_activity_btn.clicked.connect(
            lambda: self.store_parameters("activity")
        )
        self.activity_table.new_parameter.connect(
            lambda: self.save_activity_btn.setEnabled(True)
        )
        self.show_order.stateChanged.connect(self.activity_order_column)
        self.uncertainty_columns.stateChanged.connect(
            self.hide_uncertainty_columns
        )

    def _construct_layout(self):
        """ Construct the widget layout for the variable parameters tab
        """
        layout = QVBoxLayout()

        self.uncertainty_columns.setChecked(False)
        row = QToolBar()
        row.addWidget(header("Parameters "))
        row.addWidget(self.uncertainty_columns)
        row.addAction(
            qicons.question, "About brightway parameters",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())

        row = QHBoxLayout()
        row.addWidget(header("Project:"))
        row.addWidget(self.new_project_param)
        row.addWidget(self.save_project_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.project_table)

        row = QHBoxLayout()
        row.addWidget(header("Database:"))
        row.addWidget(self.new_database_param)
        row.addWidget(self.save_database_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.database_table)

        row = QHBoxLayout()
        row.addWidget(header("Activity:"))
        row.addWidget(self.save_activity_btn)
        row.addWidget(self.show_order)
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
        self.hide_uncertainty_columns()
        self.activity_order_column()

    @pyqtSlot()
    def hide_uncertainty_columns(self):
        show = self.uncertainty_columns.isChecked()
        for table in self.tables.values():
            table.uncertainty_columns(show)

    @pyqtSlot()
    def activity_order_column(self) -> None:
        col = self.activity_table.combine_columns().index("order")
        state = self.show_order.isChecked()
        if not state:
            self.activity_table.setColumnHidden(col, True)
        else:
            self.activity_table.setColumnHidden(col, False)
            self.activity_table.resizeColumnToContents(col)

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
        if name not in self.tables:
            return

        table = self.tables[name]
        error = table.save_parameters()
        if not error:
            table.sync(table.build_df())
        elif error == QMessageBox.Discard:
            # Tables are rebuilt and new parameters are dropped
            self.build_tables()
        elif error == QMessageBox.Cancel:
            # Nothing is done, errors remain for user to correct
            return
        # On a successful save or a discard, disable the save button again.
        self.buttons[name].setEnabled(False)


class ParameterExchangesTab(BaseRightTab):
    """ Overview of exchanges

    This tab shows a foldable treeview table containing all of the
    parameters set for the current project.

    Changes made to parameters in the `Definitions` tab will require
    the user to press `Recalculate exchanges` to ensure the amounts in
    the exchanges are properly updated.
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
