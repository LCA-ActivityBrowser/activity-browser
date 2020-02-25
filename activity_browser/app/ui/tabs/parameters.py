# -*- coding: utf-8 -*-
import uuid

import brightway2 as bw
from bw2data.filesystem import safe_filename
from PySide2.QtCore import Slot, QSize
from PySide2.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QToolBar,
    QStyle, QVBoxLayout, QTabWidget
)
from xlsxwriter.exceptions import FileCreateError

from ...bwutils import presamples as ps_utils
from ...settings import project_settings
from ...signals import signals
from ..icons import qicons
from ..style import header, horizontal_line
from ..tables import (
    ActivityParameterTable, DataBaseParameterTable, ExchangesTable,
    ProjectParameterTable, ScenarioTable
)
from ..widgets import ForceInputDialog
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
            "Scenarios": PresamplesTab(self),
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

        self.new_project_param = QPushButton(qicons.add, "New")
        self.database_header = header("Database:")
        self.new_database_param = QPushButton(qicons.add, "New")
        self.show_order = QCheckBox("Show order column", self)
        self.show_database_params = QCheckBox("Show database parameters", self)
        self.uncertainty_columns = QCheckBox("Show uncertainty columns", self)

        self._construct_layout()
        self._connect_signals()

        self.explain_text = """
<p>Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.</p>
<p>Note that parameters can store 
<a href="https://docs.brightwaylca.org/intro.html#storing-uncertain-values">uncertain values</a>, but these are
completely optional.</p>

<h3>In general:</h3>
<p>All parameters must have a <em>name</em> and <em>amount</em>. A <em>formula</em> is optional.</p>
<p>The formula is stored as a string that is interpreted by brightway. Python builtin functions and Numpy functions
can be used within the formula!</p>
<p>Parameters can only be deleted if they are not used in formulas of other parameters.</p>

<h3>Activity</h3>
<p>New parameters are added either by drag-and-dropping activities from the database table or by adding
 a formula to an activity exchange within the Activity tab.</p>
<ul>
<li>Only activities from editable databases can be parameterized.</li>
<li>Multiple parameters can be created for a single activity.</li>
<li>The parameter <em>name</em> must be unique within the group of parameters for an activity.</li>
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
        self.show_order.stateChanged.connect(self.activity_order_column)
        self.uncertainty_columns.stateChanged.connect(
            self.hide_uncertainty_columns
        )
        self.show_database_params.stateChanged.connect(
            self.hide_database_parameter
        )

    def _construct_layout(self):
        """ Construct the widget layout for the variable parameters tab
        """
        layout = QVBoxLayout()

        self.uncertainty_columns.setChecked(False)
        row = QToolBar()
        row.addWidget(header("Parameters "))
        row.addWidget(self.show_database_params)
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
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.project_table)

        row = QHBoxLayout()
        row.addWidget(self.database_header)
        row.addWidget(self.new_database_param)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.database_table)

        row = QHBoxLayout()
        row.addWidget(header("Activity:"))
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
        self.hide_database_parameter()
        # Cannot create database parameters without databases
        if not bw.databases:
            self.new_database_param.setEnabled(False)
        else:
            self.new_database_param.setEnabled(True)

    @Slot()
    def hide_uncertainty_columns(self):
        show = self.uncertainty_columns.isChecked()
        for table in self.tables.values():
            table.uncertainty_columns(show)

    @Slot()
    def activity_order_column(self) -> None:
        col = self.activity_table.combine_columns().index("order")
        state = self.show_order.isChecked()
        if not state:
            self.activity_table.setColumnHidden(col, True)
        else:
            self.activity_table.setColumnHidden(col, False)
            self.activity_table.resizeColumnToContents(col)

    @Slot()
    def hide_database_parameter(self) -> None:
        hide = not self.show_database_params.isChecked()
        self.database_header.setHidden(hide)
        self.new_database_param.setHidden(hide)
        self.database_table.setHidden(hide)


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
<p>Please see the <a href="https://docs.brightwaylca.org/intro.html#parameterized-datasets">Brightway2 documentation</a>
for the full explanation.</p>

<p>Shown here is an overview of all the parameters set on the current project.</p>
"""

    def _connect_signals(self):
        signals.project_selected.connect(self.build_tables)
        signals.parameters_changed.connect(self.build_tables)

    def _construct_layout(self):
        """ Construct the widget layout for the exchanges parameters tab
        """
        layout = QVBoxLayout()
        row = QToolBar()
        row.addWidget(header("Complete parameters overview "))
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
        self.table.sync()


class PresamplesTab(BaseRightTab):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.load_btn = QPushButton(qicons.add, "Load scenario table")
        self.save_btn = QPushButton(
            self.style().standardIcon(QStyle.SP_DialogSaveButton),
            "Save scenario table"
        )
        self.calculate_btn = QPushButton(
            qicons.calculate, "Process scenario table for LCA calculations"
        )
        self.hide_group = QCheckBox("Show group column")

        self.tbl = ScenarioTable(self)

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        self.load_btn.clicked.connect(self.select_read_file)
        self.save_btn.clicked.connect(self.save_scenarios)
        self.calculate_btn.clicked.connect(self.calculate_scenarios)
        self.hide_group.toggled.connect(self.tbl.group_column)
        signals.project_selected.connect(self.build_tables)
        signals.parameters_changed.connect(self.tbl.rebuild_table)
        signals.parameter_renamed.connect(self.tbl.update_param_name)

    def _construct_layout(self):
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(header("Parameter Scenarios"))
        layout.addLayout(row)
        layout.addWidget(horizontal_line())
        row = QHBoxLayout()
        row.addWidget(self.load_btn)
        row.addWidget(self.save_btn)
        row.addWidget(self.calculate_btn)
        row.addWidget(self.hide_group)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self.tbl)
        layout.addStretch(1)
        self.setLayout(layout)

    def build_tables(self) -> None:
        self.tbl.sync()
        self.tbl.group_column(False)

    @Slot(name="loadSenarioTable")
    def select_read_file(self):
        path, _ = QFileDialog().getOpenFileName(
            self, caption="Select prepared scenario file",
            dir=project_settings.data_dir, filter=self.tbl.EXCEL_FILTER
        )
        if path:
            df = ps_utils.load_scenarios_from_file(path)
            self.tbl.sync(df=df)

    @Slot(name="saveScenarioTable")
    def save_scenarios(self):
        filename, _ = QFileDialog().getSaveFileName(
            self, caption="Save current scenarios to Excel",
            dir=project_settings.data_dir, filter=self.tbl.EXCEL_FILTER
        )
        if filename:
            try:
                ps_utils.save_scenarios_to_file(self.tbl.dataframe, filename)
            except FileCreateError as e:
                QMessageBox.warning(
                    self, "File save error",
                    "Cannot save the file, please see if it is opened elsewhere or "
                    "if you are allowed to save files in that location:\n\n{}".format(e),
                    QMessageBox.Ok, QMessageBox.Ok
                )

    @Slot(name="createPresamplesPackage")
    def calculate_scenarios(self):
        if not ps_utils.PresamplesParameterManager.has_parameterized_exchanges():
            QMessageBox.warning(
                self, "No parameterized exchanges",
                "Please set formulas on exchanges to make use of scenario analysis.",
                QMessageBox.Ok, QMessageBox.Ok
            )
            return
        dialog = ForceInputDialog.get_text(
            self, "Add label", "Add a label to the calculated scenarios"
        )
        if dialog.exec_() == ForceInputDialog.Accepted:
            result = dialog.output
            if result in ps_utils.find_all_package_names():
                overwrite = QMessageBox.question(
                    self, "Label already in use", "Overwrite the old calculations?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if overwrite == QMessageBox.Yes:
                    older = ps_utils.get_package_path(result)
                    ps_utils.remove_package(older)
                    self.build_presamples_packages(safe_filename(result, False))
            else:
                self.build_presamples_packages(safe_filename(result, False))

    def build_presamples_packages(self, name: str):
        """ Calculate and store presamples arrays from parameter scenarios.
        """
        ppm = ps_utils.PresamplesParameterManager()
        names, data = zip(*self.tbl.iterate_scenarios())
        ps_id, path = ppm.presamples_from_scenarios(name, zip(names, data))
        description = "{}".format(tuple(names))
        ppm.store_presamples_as_resource(name, path, description)
        signals.presample_package_created.emit(name)
