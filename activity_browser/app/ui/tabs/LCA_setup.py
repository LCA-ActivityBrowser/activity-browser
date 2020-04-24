# -*- coding: utf-8 -*-
from collections import namedtuple

from PySide2 import QtWidgets
from PySide2.QtCore import Slot, Qt
from brightway2 import calculation_setups

from ...bwutils.superstructure import (
    all_flows_found, all_activities_found, import_from_excel, fill_df_keys_with_fields,
    scenario_names_from_df, all_exchanges_found, filter_existing_exchanges,
)
from ...signals import signals
from ..icons import qicons
from ..style import horizontal_line, header
from ..tables import (
    CSActivityTable, CSList, CSMethodsTable, PresamplesList, ScenarioImportTable
)
from ..widgets import ExcelReadDialog

"""
Lifecycle of a calculation setup
================================

Data format
-----------

{name: {'inv': [{key: amount}], 'ia': [method]}}

Responsibilities
----------------

``CalculationSetupTab`` manages whether the activities and methods tables are shown, and which buttons are shown.

``CSActivityTableWidget`` and ``CSMethodsTableWidget`` mangage drag and drop events, and use signals to communicate data changes with the controller.

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
PresamplesTuple = namedtuple("presamples", ["label", "list", "button"])


class LCASetupTab(QtWidgets.QWidget):
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
        self.rename_cs_button = QtWidgets.QPushButton(qicons.edit, "Rename")
        self.delete_cs_button = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.calculation_type = QtWidgets.QComboBox()
        self.calculation_type.addItems(["Standard LCA", "Scenario-based LCA"])
        self.calculate_button = QtWidgets.QPushButton(qicons.calculate, "Calculate")
        self.presamples = PresamplesTuple(
            QtWidgets.QLabel("Prepared scenarios:"),
            PresamplesList(self),
            QtWidgets.QPushButton(qicons.calculate, "Calculate"),
        )
        for obj in self.presamples:
            obj.hide()

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(header('Calculation Setups:'))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.rename_cs_button)
        name_row.addWidget(self.delete_cs_button)
        name_row.addStretch(1)

        calc_row = QtWidgets.QHBoxLayout()
        calc_row.addWidget(self.calculate_button)
        calc_row.addWidget(self.presamples.button)
        calc_row.addWidget(self.calculation_type)
        calc_row.addWidget(self.presamples.label)
        calc_row.addWidget(self.presamples.list)
        calc_row.addStretch(1)

        container = QtWidgets.QVBoxLayout()
        container.addLayout(name_row)
        container.addLayout(calc_row)
        container.addWidget(horizontal_line())

        cs_panel_layout.addWidget(header('Functional units:'))
        cs_panel_layout.addWidget(self.activities_table)
        cs_panel_layout.addWidget(horizontal_line())
        cs_panel_layout.addWidget(header('Impact categories:'))
        cs_panel_layout.addWidget(self.methods_table)

        self.cs_panel.setLayout(cs_panel_layout)
        container.addWidget(self.cs_panel)
        container.addWidget(self.scenario_panel)

        self.setLayout(container)

        self.connect_signals()

    def connect_signals(self):
        # Signals
        self.calculate_button.clicked.connect(self.start_calculation)
        self.presamples.button.clicked.connect(self.presamples_calculation)

        self.new_cs_button.clicked.connect(signals.new_calculation_setup.emit)
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
        signals.set_default_calculation_setup.connect(self.valid_presamples)
        signals.project_selected.connect(self.set_default_calculation_setup)
        signals.project_selected.connect(self.valid_presamples)
        signals.calculation_setup_selected.connect(lambda: self.show_details())
        signals.calculation_setup_selected.connect(self.enable_calculations)
        signals.calculation_setup_changed.connect(self.enable_calculations)
        signals.calculation_setup_changed.connect(self.valid_presamples)
        signals.presample_package_created.connect(self.valid_presamples)

    def save_cs_changes(self):
        name = self.list_widget.name
        if name:
            calculation_setups[name] = {
                'inv': self.activities_table.to_python(),
                'ia': self.methods_table.to_python()
            }

    def start_calculation(self):
        signals.lca_calculation.emit(self.list_widget.name)

    def presamples_calculation(self):
        signals.lca_presamples_calculation.emit(
            self.list_widget.name, self.presamples.list.selection
        )

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

    @Slot(name="togglePresampleCalculation")
    def valid_presamples(self):
        """ Determine if calculate with presamples is active.
        """
        valid = self.calculate_button.isEnabled() and self.presamples.list.has_packages
        if valid:
            self.presamples.list.sync()
        self.presamples.list.setEnabled(valid)
        self.presamples.button.setEnabled(valid)

    def show_details(self, show: bool = True):
        self.rename_cs_button.setVisible(show)
        self.delete_cs_button.setVisible(show)
        self.list_widget.setVisible(show)
        self.activities_table.setVisible(show)
        self.methods_table.setVisible(show)

    @Slot(int, name="changeCalculationType")
    def select_calculation_type(self, index: int):
        if index == 0:
            # Standard LCA.
            self.calculate_button.show()
            for obj in self.presamples:
                obj.hide()
            self.scenario_panel.hide()
            self.cs_panel.updateGeometry()
        elif index == 1:
            # Presamples / Scenarios LCA.
            self.calculate_button.hide()
            for obj in self.presamples:
                obj.show()
            self.scenario_panel.show()
            self.cs_panel.updateGeometry()

    def enable_calculations(self):
        valid_cs = all([self.activities_table.rowCount(), self.methods_table.rowCount()])
        self.calculate_button.setEnabled(valid_cs)


class ScenarioImportPanel(QtWidgets.QWidget):
    """Special kind of QWidget that contains one or more tables side by side."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tables = []
        layout = QtWidgets.QVBoxLayout()
        row = QtWidgets.QHBoxLayout()
        self.scenario_tables = QtWidgets.QHBoxLayout()
        self.table_btn = QtWidgets.QPushButton(qicons.add, "Add")
        self.valid_btn = QtWidgets.QPushButton(qicons.calculate, "Validate")
        self.valid_btn.setEnabled(False)

        row.addWidget(header("Scenarios"))
        row.addWidget(self.table_btn)
        row.addWidget(self.valid_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addLayout(self.scenario_tables)
        layout.addStretch(1)
        self.setLayout(layout)
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.table_btn.clicked.connect(self.add_table)
        self.table_btn.clicked.connect(self.activate_validation)
        self.valid_btn.clicked.connect(self.validate_data)
        signals.project_selected.connect(self.clear_tables)

    @Slot(name="addTable")
    def add_table(self) -> None:
        new_idx = len(self.tables)
        widget = ScenarioImportWidget(new_idx, self)
        self.tables.append(widget)
        self.scenario_tables.addWidget(widget)
        self.updateGeometry()

    @Slot(int, name="removeTable")
    def remove_table(self, idx: int) -> None:
        w = self.tables.pop(idx)
        self.scenario_tables.removeWidget(w)
        w.deleteLater()
        self.updateGeometry()
        # Do not forget to update indexes!
        for i, w in enumerate(self.tables):
            w.index = i

    @Slot(name="clearTables")
    def clear_tables(self) -> None:
        """Clear all scenario tables in certain cases (eg. project change)."""
        for w in self.tables:
            self.scenario_tables.removeWidget(w)
            w.deleteLater()
        self.tables = []
        self.updateGeometry()
        self.valid_btn.setEnabled(False)

    @Slot(name="activateValidation")
    def activate_validation(self) -> None:
        """Whenever a table action is taken, determine if the 'validate'
        button should be active or not.
        """
        load_valid = all(w.table.rowCount() > 0 for w in self.tables)
        self.valid_btn.setEnabled(load_valid)

    @Slot(name="validateData")
    def validate_data(self) -> None:
        """Ensure all the scenario superstructure exchanges exist in the
        current project databases.

        This should check multiple states:
        - All processes/flows from the files exist in the project.
        - All processes/flows have keys, these will be added if missing.
        - All exchanges from the files exist in the project.
        """
        title = "Information is missing"
        flows_valid = all(all_flows_found(w.scenario_df) for w in self.tables)
        if not flows_valid:
            QtWidgets.QMessageBox. warning(
                self, title, "Biosphere flows from the file(s) are missing",
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
            )
            return
        proc_valid = all(all_activities_found(w.scenario_df) for w in self.tables)
        if not proc_valid:
            QtWidgets.QMessageBox. warning(
                self, title, "Process flows from the file(s) are missing",
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
            )
            return
        exc_valid = all(all_exchanges_found(w.scenario_df) for w in self.tables)
        if not exc_valid:
            # Initial failure, is this caused by keys missing?
            for w in self.tables:
                w.scenario_df = fill_df_keys_with_fields(w.scenario_df)
            exc_valid = all(all_exchanges_found(w.scenario_df) for w in self.tables)
        if not exc_valid:
            missing = (filter_existing_exchanges(w.scenario_df) for w in self.tables)
            iterable = iter(missing)
            first = next(iterable)
            for s in iterable:
                first = first.append(s)
            msgbox = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Warning, title,
                "Exchanges from the file(s) are missing",
                QtWidgets.QMessageBox.Ok, self
            )
            msgbox.setWindowModality(Qt.ApplicationModal)
            msgbox.setDetailedText("Missing exchanges: {}".format(first.unique()))
            msgbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgbox.exec_()
            return
        # Nothing popped? Hooray!
        QtWidgets.QMessageBox.information(
            self, "Success", "Given scenario files are valid!",
            QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
        )


class ScenarioImportWidget(QtWidgets.QWidget):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)

        self.index = index
        self.scenario_name = QtWidgets.QLabel("<filename>", self)
        self.load_btn = QtWidgets.QPushButton(qicons.import_db, "Load")
        self.remove_btn = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.table = ScenarioImportTable(self)
        self.scenario_df = None

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
            self.load_btn.clicked.connect(parent.activate_validation)
            self.remove_btn.clicked.connect(
                lambda: parent.remove_table(self.index)
            )

    @Slot(name="loadScenarioFile")
    def load_action(self) -> None:
        dialog = ExcelReadDialog(self)
        if dialog.exec_() == ExcelReadDialog.Accepted:
            path = dialog.path
            idx = dialog.sheet_index.value()
            try:
                self.scenario_df = import_from_excel(path, idx)
                cols = scenario_names_from_df(self.scenario_df)
                self.table.sync(cols)
                self.scenario_name.setText(path.name)
            except (IndexError, ValueError) as e:
                print(e)
                QtWidgets.QMessageBox.warning(
                    self, "Something went wrong", str(e),
                    QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
                )
