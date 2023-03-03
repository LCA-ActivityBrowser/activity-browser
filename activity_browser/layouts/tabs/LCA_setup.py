# -*- coding: utf-8 -*-
from typing import Optional, Union

from PySide2 import QtWidgets
from PySide2.QtCore import Slot, Qt
from brightway2 import calculation_setups
import pandas as pd

from ...bwutils.superstructure import (
    SuperstructureManager, import_from_excel, scenario_names_from_df,
    SUPERSTRUCTURE, _time_it_, ABCSVImporter, ABFeatherImporter,
    ABFileImporter
)
from ...signals import signals
from ...ui.icons import qicons
from ...ui.style import horizontal_line, header, style_group_box
from ...ui.tables import (
    CSActivityTable, CSList, CSMethodsTable, ScenarioImportTable
)
from ...ui.widgets import ExcelReadDialog
from .base import BaseRightTab

"""
Lifecycle of a calculation setup
================================

Data format
-----------

{name: {'inv': [{key: amount}], 'ia': [method]}}

Responsibilities
----------------

``CalculationSetupTab`` manages whether the activities and methods tables are shown, and which buttons are shown.

``CSActivityTableWidget`` and ``CSMethodsTableWidget`` manage drag and drop events, and use signals to communicate data changes with the controller.

Initiation
----------

The app is started, a default project is loaded. ``CalculationSetupTab`` is initiated. If a calculation setup is present, the first one in a sorted list is selected. The signal ``calculation_setup_selected`` is emitted. Activity and methods tables are shown, as well as the full button row. If no calculation setup is available, all tables and most buttons are hidden, only the ``new_cs_button`` is shown.

``calculation_setup_selected`` is received by ``CSList``, which sets the list index correctly.

``calculation_setup_selected`` is received by ``CSActivityTableWidget`` and ``CSMethodsTableWidget``, and data is displayed.

Selecting a new project
-----------------------

When a new project is selected, the signal ``project_selected`` is received by ``CalculationSetupTab``, which follows the same procedure: emit ``calculation_setup_selected`` is possible, otherwise hide tables and buttons.

Selecting a different calculation setup
---------------------------------------

When a new calculation setup is selected in ``CSList``, the event ``itemSelectionChanged`` calls a function that emits ``calculation_setup_selected``.

Altering the current calculation setup
--------------------------------------

When new activities or methods are dragged into the activity or methods tables, the signal ``calculation_setup_changed`` is emitted. ``calculation_setup_changed`` is received by a controller method ``write_current_calculation_setup`` which saves the current data.

When the amount of an activity is changed, the event ``cellChanged`` is caught by ``CSActivityTableWidget``, which emits ``calculation_setup_changed``.

Creating a new calculation setup
--------------------------------

The button ``new_cs_button`` is connected to the controller method ``new_calculation_setup``, which creates the new controller setup and in turn emits ``calculation_setup_selected``. Note that ``CSList`` rebuilds the list of all calculation setups when receiving ``calculation_setup_selected``, so the new setup is listed.

Renaming a calculation setup
----------------------------

The button ``rename_cs_button`` is connected to the controller method ``rename_calculation_setup``, which changes the calculation setup name and in turn emits ``calculation_setup_selected``.

Deleting a calculation setup
----------------------------

The button ``delete_cs_button`` is connected to the controller method ``delete_calculation_setup``, which deletes the calculation setup name and in turn emits ``calculation_setups_changed``.

State data
----------

The currently selected calculation setup is retrieved by getting the currently selected value in ``CSList``.

"""

class LCASetupTab(QtWidgets.QWidget):
    DEFAULT = 0
    SCENARIOS = 1

    def __init__(self, parent=None):
        super().__init__(parent)

        self.cs_panel = QtWidgets.QWidget(self)
        cs_panel_layout = QtWidgets.QVBoxLayout()
        self.scenario_panel = ScenarioImportPanel(self)
        self.scenario_panel.hide()

        self.activities_table = CSActivityTable(self)
        self.methods_table = CSMethodsTable(self)
        self.list_widget = CSList(self)

        self.new_cs_button = QtWidgets.QPushButton(qicons.add, "New")
        self.copy_cs_button = QtWidgets.QPushButton(qicons.copy, "Copy")
        self.rename_cs_button = QtWidgets.QPushButton(qicons.edit, "Rename")
        self.delete_cs_button = QtWidgets.QPushButton(qicons.delete, "Delete")

        self.calculate_button = QtWidgets.QPushButton(qicons.calculate, "Calculate")
        self.calculation_type = QtWidgets.QComboBox()
        self.calculation_type.addItems(["Standard LCA", "Scenario LCA"])

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(header('Calculation Setup:'))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.copy_cs_button)
        name_row.addWidget(self.rename_cs_button)
        name_row.addWidget(self.delete_cs_button)
        name_row.addStretch(1)

        calc_row = QtWidgets.QHBoxLayout()
        calc_row.addWidget(self.calculate_button)
        calc_row.addWidget(self.calculation_type)
        calc_row.addStretch(1)

        container = QtWidgets.QVBoxLayout()
        container.addLayout(name_row)
        container.addLayout(calc_row)
        container.addWidget(horizontal_line())

        # widget for the reference flows
        self.reference_flow_widget = QtWidgets.QWidget()
        reference_flow_layout = QtWidgets.QVBoxLayout()
        reference_flow_layout.addWidget(header('Reference flows:'))
        reference_flow_layout.addWidget(self.activities_table)
        self.reference_flow_widget.setLayout(reference_flow_layout)

        # widget for the impact categories
        self.impact_categories_widget = QtWidgets.QWidget()
        impact_categories_layout = QtWidgets.QVBoxLayout()
        impact_categories_layout.addWidget(header('Impact categories:'))
        impact_categories_layout.addWidget(self.methods_table)
        self.impact_categories_widget.setLayout(impact_categories_layout)

        # splitter widget to combine the two above widgets
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.reference_flow_widget)
        self.splitter.addWidget(self.impact_categories_widget)

        self.no_setup_label = QtWidgets.QLabel("To do an LCA, create a new calculation setup first by pressing 'New'.")
        cs_panel_layout.addWidget(self.no_setup_label)
        cs_panel_layout.addWidget(self.splitter)

        self.cs_panel.setLayout(cs_panel_layout)
        container.addWidget(self.cs_panel)
        container.addWidget(self.scenario_panel)

        self.setLayout(container)

        self.connect_signals()

    def connect_signals(self):
        # Signals
        self.calculate_button.clicked.connect(self.start_calculation)

        self.new_cs_button.clicked.connect(signals.new_calculation_setup.emit)
        self.copy_cs_button.clicked.connect(
            lambda: signals.copy_calculation_setup.emit(self.list_widget.name)
        )
        self.delete_cs_button.clicked.connect(
            lambda x: signals.delete_calculation_setup.emit(
                self.list_widget.name
        ))
        self.rename_cs_button.clicked.connect(
            lambda x: signals.rename_calculation_setup.emit(
                self.list_widget.name
        ))
        signals.calculation_setup_changed.connect(self.save_cs_changes)
        self.calculation_type.currentIndexChanged.connect(self.select_calculation_type)

        # Slots
        signals.set_default_calculation_setup.connect(self.set_default_calculation_setup)
        signals.project_selected.connect(self.set_default_calculation_setup)
        signals.calculation_setup_selected.connect(lambda: self.show_details())
        signals.calculation_setup_selected.connect(self.enable_calculations)
        signals.calculation_setup_changed.connect(self.enable_calculations)

    def save_cs_changes(self):
        name = self.list_widget.name
        if name:
            calculation_setups[name] = {
                'inv': self.activities_table.to_python(),
                'ia': self.methods_table.to_python()
            }

    @Slot(name="calculationDefault")
    def start_calculation(self):
        """Check what calculation type is selected and send the correct data signal."""

        calc_type = self.calculation_type.currentIndex()
        if calc_type == self.DEFAULT:
            # Standard LCA
            data = {
                'cs_name': self.list_widget.name,
                'calculation_type': 'simple',
            }
        elif calc_type == self.SCENARIOS:
            # Scenario LCA
            data = {
                'cs_name': self.list_widget.name,
                'calculation_type': 'scenario',
                'data': self.scenario_panel.scenario_dataframe(),
            }
        else:
            return

        signals.lca_calculation.emit(data)

    @Slot(name="toggleDefaultCalculation")
    def set_default_calculation_setup(self):
        self.calculation_type.setCurrentIndex(0)
        if not len(calculation_setups):
            self.show_details(False)
            self.calculate_button.setEnabled(False)
        else:
            signals.calculation_setup_selected.emit(
                sorted(calculation_setups)[0]
            )

    def show_details(self, show: bool = True):
        # show/hide items from name_row
        self.rename_cs_button.setVisible(show)
        self.delete_cs_button.setVisible(show)
        self.copy_cs_button.setVisible(show)
        self.list_widget.setVisible(show)
        # show/hide items from calc_row
        self.calculate_button.setVisible(show)
        self.calculation_type.setVisible(show)
        # show/hide tables widgets
        self.splitter.setVisible(show)
        self.no_setup_label.setVisible(not(show))

    @Slot(int, name="changeCalculationType")
    def select_calculation_type(self, index: int):
        if index == self.DEFAULT:
            # Standard LCA
            self.scenario_panel.hide()
        elif index == self.SCENARIOS:
            # Scenario LCA
            self.scenario_panel.show()
        self.cs_panel.updateGeometry()

    def enable_calculations(self):
        valid_cs = all([self.activities_table.rowCount(), self.methods_table.rowCount()])
        self.calculate_button.setEnabled(valid_cs)


class ScenarioImportPanel(BaseRightTab):
    MAX_TABLES = 5

    """Special kind of QWidget that contains one or more tables side by side."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.explain_text = """
        <p>You can import <b>two types of scenario files</b> here:</h4>
        <p>1. <b>Flow-scenarios</b>: alternative values for exchanges (technosphere/biosphere flows) 
        (<i>scenario difference files</i>)</p>
        <p>2. <b>Parameter-scenarios</b>: alternative values for parameters <i>(parameter scenarios files)</i></p>
        
        Further information is provided in this <a href="https://www.youtube.com/watch?v=3LPcpV1G_jg">video</a>. 
        
        <p>If you need a template for these files, you can go to the <i>Parameters > Scenarios tab</i>. 
        Then click <i>Export parameter-scenarios</i> to obtain a parameter-scenarios file or   
        <i>Export as flow-scenarios</i> to obtain a flow-scenarios file 
        (you need at least one parameterized activity for the latter).</p> 
        
        <br> <p> You can also work with <b>multiple scenario files</b> for which there are with two options:</p>
        <p>1. <b>Combine scenarios</b>: this yields all possible scenario combinations 
        (e.g. file 1: <i>S1, S2</i> and file 2: <i>A, B</i> yields <i>S1-A, S1-B, S2-A, S2-B</i>)</p>
        <p>2. <b>Extend scenarios</b>: scenarios from file 2 extend scenarios of file 1 
        (only possible if scenario names are identical in all files, e.g. everywhere <i>S1, S2</i>).</p> 
        """

        self.tables = []
        layout = QtWidgets.QVBoxLayout()

        self.scenario_tables = QtWidgets.QHBoxLayout()
        self.table_btn = QtWidgets.QPushButton(qicons.add, "Add")

        self.group_box = QtWidgets.QGroupBox()
        self.group_box.setStyleSheet(style_group_box.border_title)
        input_field_layout = QtWidgets.QHBoxLayout()
        self.group_box.setLayout(input_field_layout)
        self.combine_group = QtWidgets.QButtonGroup()
        self.combine_group.setExclusive(True)
        self.product_choice = QtWidgets.QCheckBox("Combine scenarios")
        self.product_choice.setChecked(True)
        self.addition_choice = QtWidgets.QCheckBox("Extend scenarios")
        self.combine_group.addButton(self.product_choice)
        self.combine_group.addButton(self.addition_choice)
        input_field_layout.addWidget(self.product_choice)
        input_field_layout.addWidget(self.addition_choice)
        self.group_box.setHidden(True)

        row = QtWidgets.QToolBar()
        row.addWidget(header("Scenarios:"))
        row.addAction(
            qicons.question, "Scenarios help",
            self.explanation
        )
        row.addWidget(self.table_btn)
        tool_row = QtWidgets.QHBoxLayout()
        tool_row.addWidget(row)
        tool_row.addWidget(self.group_box)
        tool_row.addStretch(1)
        layout.addLayout(tool_row)
        layout.addLayout(self.scenario_tables)
        layout.addStretch(1)
        self.setLayout(layout)
        self._connect_signals()
        self._scenario_dataframe = None

    def _connect_signals(self) -> None:
        self.table_btn.clicked.connect(self.add_table)
        self.table_btn.clicked.connect(self.can_add_table)
        signals.project_selected.connect(self.clear_tables)
        signals.project_selected.connect(self.can_add_table)
        signals.parameter_superstructure_built.connect(self.handle_superstructure_signal)

    def scenario_dataframe(self):
        return self._scenario_dataframe

    def scenario_names(self, idx: int) -> list:
        if idx > len(self.tables):
            return []
        return scenario_names_from_df(self.tables[idx])

    def combined_dataframe(self) -> pd.DataFrame:
        """Return a dataframe that combines the scenarios of multiple tables.
        """
        if not self.tables:
            # Return an empty dataframe, will almost immediately cause a
            # validation exception.
            return pd.DataFrame()
        data = [df for df in (t.dataframe for t in self.tables) if not df.empty]
        if not data:
            return pd.DataFrame()
        manager = SuperstructureManager(*data)
        if self.product_choice.isChecked():
            kind = "product"
        elif self.addition_choice.isChecked():
            kind = "addition"
        else:
            kind = "none"
        self._scenario_dataframe = manager.combined_data(kind, ABFileImporter.check_duplicates)

    @Slot(name="addTable")
    def add_table(self) -> None:
        new_idx = len(self.tables)
        widget = ScenarioImportWidget(new_idx, self)
        self.tables.append(widget)
        self.scenario_tables.addWidget(widget)
        self.updateGeometry()
        self.combined_dataframe()

    @Slot(int, name="removeTable")
    def remove_table(self, idx: int) -> None:
        w = self.tables.pop(idx)
        self.scenario_tables.removeWidget(w)
        w.deleteLater()
        self.updateGeometry()
        # Do not forget to update indexes!
        for i, w in enumerate(self.tables):
            w.index = i
        self.combined_dataframe()

    @Slot(name="clearTables")
    def clear_tables(self) -> None:
        """Clear all scenario tables in certain cases (eg. project change)."""
        for w in self.tables:
            self.scenario_tables.removeWidget(w)
            w.deleteLater()
        self.tables = []
        self.updateGeometry()
        self.combined_dataframe()

    def updateGeometry(self):
        self.group_box.setHidden(len(self.tables) <= 1)
        # Make sure that scenario tables are equally balanced within the box.
        if self.tables:
            table_width = self.width() / len(self.tables)
            for table in self.tables:
                table.setMaximumWidth(table_width)
        super().updateGeometry()

    @Slot(name="canAddTable")
    def can_add_table(self) -> None:
        """Use this to set a hardcoded limit on the amount of scenario tables
        a user can add.
        """
        self.table_btn.setEnabled(len(self.tables) < self.MAX_TABLES)

    @Slot(int, object, name="handleSuperstructureSignal")
    def handle_superstructure_signal(self, table_idx: int, df: pd.DataFrame) -> None:
        table = self.tables[table_idx]
        table.sync_superstructure(df)


class ScenarioImportWidget(QtWidgets.QWidget):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.index = index
        self.scenario_name = QtWidgets.QLabel("<filename>", self)
        self.load_btn = QtWidgets.QPushButton(qicons.import_db, "Load")
        self.load_btn.setToolTip("Load (new) data for this scenario table")
        self.remove_btn = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.remove_btn.setToolTip("Remove this scenario table")
        self.table = ScenarioImportTable(self)
        self.scenario_df = pd.DataFrame(columns=SUPERSTRUCTURE)

        layout = QtWidgets.QVBoxLayout()

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.scenario_name)
        row.addWidget(self.load_btn)
        row.addStretch(1)
        row.addWidget(self.remove_btn)

        layout.addLayout(row)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self._connect_signals()

    def _connect_signals(self):
        self.load_btn.clicked.connect(self.load_action)
        parent = self.parent()
        if parent and isinstance(parent, ScenarioImportPanel):
            self.remove_btn.clicked.connect(
                lambda: parent.remove_table(self.index)
            )
            self.remove_btn.clicked.connect(parent.can_add_table)


    @_time_it_
    @Slot(name="loadScenarioFile")
    def load_action(self) -> None:
        dialog = ExcelReadDialog(self)
        if dialog.exec_() == ExcelReadDialog.Accepted:
            path = dialog.path
            idx = dialog.import_sheet.currentIndex()
            file_type_suffix = dialog.path.suffix
            separator = dialog.field_separator.currentData()
            print("separator == '{}'".format(separator))
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            print('Loading Scenario file. This may take a while for large files')
            try:
                # Try and read as a superstructure file
                if file_type_suffix == ".feather":
                    df = ABFeatherImporter.read_file(path)
#                    ABFeatherImporter.all_checks(df, ABCSVImporter.ABScenarioColumnsErrorIfNA, ABCSVImporter.scenario_names(df))

                elif file_type_suffix.startswith(".xls"):
                    df = import_from_excel(path, idx)
                else:
                    df = ABCSVImporter.read_file(path, separator=separator)
#                    ABCSVImporter.all_checks(df, ABCSVImporter.ABScenarioColumnsErrorIfNA, ABCSVImporter.scenario_names(df))
                df = ABFileImporter.check_duplicates(df)
                if df is None:
                    QtWidgets.QApplication.restoreOverrideCursor()
                    return
                self.sync_superstructure(df)
            except (IndexError, ValueError) as e:
                # Try and read as parameter scenario file.
                print("Superstructure: {}\nAttempting to read as parameter scenario file.".format(e))
                df = pd.read_excel(path, sheet_name=idx, engine="openpyxl")
                include_default = True
                if "default" not in df.columns:
                    query = QtWidgets.QMessageBox.question(
                        self, "Default column not found",
                        "Attempt to load and include the 'default' scenario column?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        QtWidgets.QMessageBox.No
                    )
                    if query == QtWidgets.QMessageBox.No:
                        include_default = False
                signals.parameter_scenario_sync.emit(self.index, df, include_default)
            finally:
                self.scenario_name.setText(path.name)
                self.scenario_name.setToolTip(path.name)
                QtWidgets.QApplication.restoreOverrideCursor()

    @_time_it_
    def sync_superstructure(self, df: pd.DataFrame) -> None:
        # TODO: Move the 'scenario_df' into the model itself.
        self.scenario_df = df
        cols = scenario_names_from_df(self.scenario_df)
        self.table.model.sync(cols)
        self._parent.combined_dataframe()

    @property
    def dataframe(self) -> pd.DataFrame:
        if self.scenario_df.empty:
            print("No data in scenario table {}, skipping".format(self.index + 1))
        return self.scenario_df
