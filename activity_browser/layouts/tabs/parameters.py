# -*- coding: utf-8 -*-
from pathlib import Path

import brightway2 as bw
import pandas as pd
from PySide2.QtCore import Slot, QSize, Qt
from PySide2.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QToolBar,
    QStyle, QVBoxLayout, QTabWidget, QSplitter, QWidget, QAbstractButton
)
from xlsxwriter.exceptions import FileCreateError

from ...bwutils.manager import ParameterManager
from ...signals import signals
from ...ui.icons import qicons
from ...ui.style import header, horizontal_line
from ...ui.tables import (
    ActivityParameterTable, DataBaseParameterTable, ExchangesTable,
    ProjectParameterTable, ScenarioTable, BaseParameterTable
)
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
            "Scenarios": ParameterScenariosTab(self),
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

    @Slot()
    def activity_parameter_added(self) -> None:
        """ Selects the correct sub-tab to show and trigger a switch to
        the Parameters tab.
        """
        self.setCurrentIndex(self.indexOf(self.tabs["Definitions"]))
        signals.show_tab.emit("Parameters")


class ABParameterTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = None
        self.header = None

    def create_layout(self, title: str = None, bttn: QAbstractButton = None, table: BaseParameterTable = None):
        headerLayout = QHBoxLayout()
        self.header = header(title)

        headerLayout.addWidget(self.header)
        headerLayout.addWidget(bttn)
        headerLayout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(headerLayout)
        layout.addWidget(table)
        layout.addStretch(1)
        return layout

    def get_table(self):
        return self.table


class ABProjectParameter(ABParameterTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.newParameter = QPushButton(qicons.add, "New")
        self.header = "Project:"
        self.table = ProjectParameterTable(self)

        self.setLayout(self.create_layout(self.header, self.newParameter, self.table))
        self._connect_signal()

    def _connect_signal(self):
        self.newParameter.clicked.connect(
            lambda: signals.add_parameter.emit(None)
        )


class ABDatabaseParameter(ABParameterTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.header = "Database:"
        self.newParameter = QPushButton(qicons.add, "New")
        self.table = DataBaseParameterTable(self)

        self.setLayout(self.create_layout(self.header, self.newParameter, self.table))
        self._connect_signal()

    def _connect_signal(self):
        self.newParameter.clicked.connect(
            lambda: signals.add_parameter.emit(("db", ""))
        )

    def set_enabled(self, trigger):
        if not bw.databases:
            self.newParameter.setEnabled(False)
        else:
            self.newParameter.setEnabled(True)


class ABActivityParameter(ABParameterTable):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.header="Activity:"
        self.parameter = QCheckBox("Show order column", self)
        self.table = ActivityParameterTable(self)

        self.setLayout(self.create_layout(self.header, self.parameter, self.table))
        self._connect_signal()

    def _connect_signal(self):
        self.parameter.stateChanged.connect(self.activity_order_column)

    @Slot()
    def activity_order_column(self) -> None:
        col = self.table.model.order_col
        state = self.parameter.isChecked()
        if not state:
            self.table.setColumnHidden(col, True)
        else:
            self.table.setColumnHidden(col, False)
            self.table.resizeColumnToContents(col)


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

        self.project_table = ABProjectParameter(self)
        self.database_table = ABDatabaseParameter(self)
        self.activity_table = ABActivityParameter(self)
        self.tables = {
            "project": self.project_table.get_table(), "database": self.database_table.get_table(),
            "activity": self.activity_table.get_table(),
        }
        for t in self.tables.values():
            t.model.sync()

#        self.new_project_param = QPushButton(qicons.add, "New")
#        self.database_header = header("Database:")
#        self.new_database_param = QPushButton(qicons.add, "New")
#        self.show_order = QCheckBox("Show order column", self)
        self.show_database_params = QCheckBox("Database parameters", self)
        self.show_database_params.setToolTip("Show/hide the database parameters")
        self.show_database_params.setChecked(True)
#        self.activity_header = header("Activity:")
        self.show_activity_params = QCheckBox("Activity parameters", self)
        self.show_activity_params.setToolTip("Show/hide the activity parameters")
        self.show_activity_params.setChecked(True)
        self.comment_column = QCheckBox("Comments", self)
        self.comment_column.setToolTip("Show/hide the comment column")
        self.hide_comment_column()
        self.uncertainty_columns = QCheckBox("Uncertainty", self)
        self.uncertainty_columns.setToolTip("Show/hide the uncertainty columns")

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>This tab is the main tab for creating and modifying parameters.</p>
<p>The scope of parameters can be either a specific activity, a database, or an entire project 
(meaning that an activity parameter can only be used within a specific activity, 
while a project parameter can be used anywhere within a project and across all databases within that project).</p>



<p><b>In general</b></p>
<p>All parameters must have a <em>name</em> and <em>amount</em>. A <em>formula</em> is optional.</p>
<p>The formula is stored as a string that is interpreted by brightway. Python builtin functions and Numpy functions
can be used within the formula!</p>
<p>Parameters can only be deleted if they are not used in formulas of other parameters.</p>
<p>Note that optionally <a href="https://2.docs.brightway.dev/intro.html#storing-uncertain-values">uncertainties</a>, can be specified for parameters.</p>

<p><b>Activity parameters</b></p>
<p>New parameters are added either by drag-and-dropping activities from the database table or by adding
 a formula to an activity exchange within the Activity tab.</p>
<ul>
<li>Only activities from editable databases can be parameterized.</li>
<li>Multiple parameters can be created for a single activity.</li>
<li>The parameter <em>name</em> must be unique within the group of parameters for an activity.</li>
<li>Note: activity parameters are also auto-generated when a project or database parameter is used in an activity that has previously not been parameterized.</li>
</ul>



<p>For more information on this topic see also the 
<a href="https://2.docs.brightway.dev/intro.html#parameterized-datasets">Brightway2 documentation</a>.</p>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_tables)
        signals.parameters_changed.connect(self.build_tables)
#        self.new_project_param.clicked.connect(
#            lambda: signals.add_parameter.emit(None)
#        )
#        self.new_database_param.clicked.connect(
#            lambda: signals.add_parameter.emit(("db", ""))
#        )
#        self.show_order.stateChanged.connect(self.activity_order_column)
        self.show_database_params.toggled.connect(
            self.hide_database_parameter
        )
        self.show_activity_params.toggled.connect(
            self.hide_activity_parameter
        )
        self.comment_column.stateChanged.connect(
            self.hide_comment_column
        )
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
        row.addWidget(self.show_database_params)
        row.addWidget(self.show_activity_params)
        row.addWidget(self.comment_column)
        row.addWidget(self.uncertainty_columns)
        row.addAction(
            qicons.question, "About brightway parameters",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())

        tables = QSplitter(Qt.Vertical)
#        row = QHBoxLayout()
#        row.addWidget(header("Project:"))
#        row.addWidget(self.new_project_param)
#        row.addStretch(1)
#        layout.addLayout(row)
        tables.addWidget(self.project_table)

#        row = QHBoxLayout()
#        row.addWidget(self.database_header)
#        row.addWidget(self.new_database_param)
#        row.addStretch(1)
#        layout.addLayout(row)
        tables.addWidget(self.database_table)

#        row = QHBoxLayout()
#        row.addWidget(self.activity_header)
#        row.addWidget(self.show_order)
#        row.addStretch(1)
#        layout.addLayout(row)
        tables.addWidget(self.activity_table)

        layout.addWidget(tables)
#        layout.addStretch(1)
        self.setLayout(layout)

    @Slot(name="rebuildParameterTables")
    def build_tables(self):
        """ Read parameters from brightway and build dataframe tables
        """
        self.hide_uncertainty_columns()
        self.activity_order_column()
        # Cannot create database parameters without databases
        if not bw.databases:
            self.database_table.set_enabled(False)
        else:
            self.database_table.set_enabled(True)

    @Slot()
    def hide_uncertainty_columns(self):
        show = self.uncertainty_columns.isChecked()
        for table in self.tables.values():
            table.uncertainty_columns(show)

    @Slot()
    def hide_comment_column(self):
        show = self.comment_column.isChecked()
        for table in self.tables.values():
            table.comment_column(show)

    @Slot()
    def activity_order_column(self) -> None:
        col = self.activity_table.get_table().model.order_col
        state = self.activity_table.parameter.isChecked()
        if not state:
            self.activity_table.get_table().setColumnHidden(col, True)
        else:
            self.activity_table.get_table().setColumnHidden(col, False)
            self.activity_table.get_table().resizeColumnToContents(col)

    @Slot(bool, name="hideDatabaseParameterTable")
    def hide_database_parameter(self, toggled: bool) -> None:
        self.database_table.header.setHidden(not toggled)
        self.database_table.newParameter.setHidden(not toggled)
        self.database_table.table.setHidden(not toggled)
        self.database_table.setHidden(not toggled)

    @Slot(bool)
    def hide_activity_parameter(self, toggled: bool) -> None:
        self.activity_table.header.setHidden(not toggled)
        self.activity_table.parameter.setHidden(not toggled)
        self.activity_table.table.setHidden(not toggled)
        self.activity_table.setHidden(not toggled)


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

        self.table = ExchangesTable(self)

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>This tab lists all exchanges within the selected project that are calculated via parameters.</p>
<p>For more information on this topic see also the 
<a href="https://2.docs.brightway.dev/intro.html#parameterized-datasets">Brightway2 documentation</a>.</p>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_tables)
        signals.parameters_changed.connect(self.build_tables)

    def _construct_layout(self):
        """ Construct the widget layout for the exchanges parameters tab
        """
        layout = QVBoxLayout()
        row = QToolBar()
        row.addWidget(header("Overview of parameterized exchanges"))
        row.setIconSize(QSize(24, 24))
        row.addAction(
            qicons.question, "About parameters overview",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())
        layout.addWidget(self.table, 2)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_tables(self) -> None:
        """ Read parameters from brightway and build tree tables
        """
        self.table.model.sync()


class ParameterScenariosTab(BaseRightTab):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.load_btn = QPushButton(qicons.add, "Import parameter-scenarios")
        self.load_btn.setToolTip(
            "Load prepared excel files with additional parameter scenarios."
        )
        self.save_btn = QPushButton(
            self.style().standardIcon(QStyle.SP_DialogSaveButton),
            "Export parameter-scenarios"
        )
        self.save_btn.setToolTip(
            "Export the current parameter scenario table to excel."
        )
        self.calculate_btn = QPushButton(
            qicons.calculate, "Export as flow-scenarios"
        )
        self.calculate_btn.setToolTip(
            ("Process the current parameter scenario table into prepared flow"
             " scenario data.")
        )
        self.reset_btn = QPushButton(qicons.history, "Reset table")
        self.reset_btn.setToolTip("Reset the scenario table, wiping any changes.")
        self.hide_group = QCheckBox("Show group column")

        self.tbl = ScenarioTable(self)
        self.tbl.setToolTip(
            "This table is not editable, use the export/import functionality"
        )

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
    <p>This tab has 3 functions:</p>
    <p>1. <b> Export parameter-scenarios </b> : this exports the table as shown below to an Excel file. You can modify it there and use 
    it in scenario LCAs (see Calculation Setup tab)</p>
    <p>2. <b>Import parameter-scenarios</b>: imports a table like the one shown below from Excel. If parameters are missing in Excel, 
    the default values will be used. IMPORTANT NOTE: the ONLY function this button serves is to display the Excel file. 
    If you want to use the Excel file in scenario LCA, please import it in the Calculation Setup tab.</p>
    <p>3. <b>Export as flow-scenarios</b>: This converts a "parameter-scenarios" file (alternative values for parameters) to a 
    "flow-scenarios" file (alternative values for the exchanges as used in LCA calculations).</p>

    <p><b>Suggested <i>workflow</i> to create scenarios for your parameters</b>:</p>
    <p>Export parameter-scenarios. This will generate an Excel file for you where you can add scenarios (columns). 
    You may want to delete rows that you intend to change or rows that are for dependent parameters (those that depend on other parameters) as these values will be overwritten by the formulas. 
    Finally, import the parameter-scenarios in the <i>Calculation Setup</i> (not here!) to perform scenario calculations (you need to select "Scenario LCA").</p>
    
    <p>For more information on this topic see also the 
    <a href="https://2.docs.brightway.dev/intro.html#parameterized-datasets">Brightway2 documentation</a>.</p>
    """

    def _connect_signals(self):
        self.load_btn.clicked.connect(self.select_read_file)
        self.save_btn.clicked.connect(self.save_scenarios)
        self.calculate_btn.clicked.connect(self.calculate_scenarios)
        self.reset_btn.clicked.connect(self.tbl.model.sync)
        self.hide_group.toggled.connect(self.tbl.group_column)
        signals.parameter_scenario_sync.connect(self.process_scenarios)

    def _construct_layout(self):
        layout = QVBoxLayout()

        row = QToolBar()
        row.addWidget(header("Parameter Scenarios"))
        row.addAction(
            qicons.question, "About parameters scenarios",
            self.explanation
        )
        layout.addWidget(row)
        layout.addWidget(horizontal_line())

        row = QHBoxLayout()
        row.addWidget(self.reset_btn)
        row.addWidget(self.save_btn)
        row.addWidget(self.load_btn)
        row.addWidget(self.calculate_btn)
        row.addWidget(self.hide_group)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.tbl)
        layout.addStretch(1)
        self.setLayout(layout)

    @Slot(int, object, bool, name="processParameterScenarios")
    def process_scenarios(self, table_idx: int, df: pd.DataFrame, default: bool) -> None:
        """Use this method to discretely process a parameter scenario file
        for the LCA setup.
        """
        try:
            self.tbl.model.sync(df=df, include_default=default)
            scenarios = self.build_flow_scenarios()
            signals.parameter_superstructure_built.emit(table_idx, scenarios)
        except AssertionError as e:
            QMessageBox.critical(
                self, "Cannot load parameters", str(e), QMessageBox.Ok, QMessageBox.Ok
            )

    @Slot(name="loadSenarioTable")
    def select_read_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, caption="Select prepared scenario file",
            filter=self.tbl.EXCEL_FILTER
        )
        if path:
            df = pd.read_excel(path, engine="openpyxl")
            self.tbl.model.sync(df=df)

    @Slot(name="saveScenarioTable")
    def save_scenarios(self):
        try:
            self.tbl.to_excel("Save current scenarios to Excel")
        except FileCreateError as e:
            QMessageBox.warning(
                self, "File save error",
                "Cannot save the file, please see if it is opened elsewhere or "
                "if you are allowed to save files in that location:\n\n{}".format(e),
                QMessageBox.Ok, QMessageBox.Ok
            )

    @Slot(name="createParameterExport")
    def calculate_scenarios(self):
        df = self.build_flow_scenarios()
        self.store_flows_to_file(df)

    def build_flow_scenarios(self) -> pd.DataFrame:
        """Calculate exchange changes for each parameter scenario and construct
        a flow scenarios template file.
        """
        from ...bwutils.superstructure import superstructure_from_arrays

        pm = ParameterManager()
        names, data = zip(*self.tbl.iterate_scenarios())
        samples, indices = pm.arrays_from_scenarios(zip(names, data))
        df = superstructure_from_arrays(samples, indices, names)
        return df

    def store_flows_to_file(self, df: pd.DataFrame) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, caption="Save calculated flow scenarios to Excel",
            filter=self.tbl.EXCEL_FILTER
        )
        if filename:
            try:
                path = Path(filename)
                path = path if path.suffix in {".xlsx", ".xls"} else path.with_suffix(".xlsx")
                df.to_excel(excel_writer=path, index=False)
            except FileCreateError as e:
                QMessageBox.warning(
                    self, "File save error",
                    "Cannot save the file, please see if it is opened elsewhere or "
                    "if you are allowed to save files in that location:\n\n{}".format(e),
                    QMessageBox.Ok, QMessageBox.Ok
                )
