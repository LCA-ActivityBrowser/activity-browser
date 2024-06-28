# -*- coding: utf-8 -*-
import pandas as pd
from PySide2 import QtWidgets
from PySide2.QtCore import Qt, Slot

from activity_browser import actions, log, signals
from activity_browser.mod import bw2data as bd

from ...bwutils.errors import *
from ...bwutils.superstructure import (SUPERSTRUCTURE, ABCSVImporter,
                                       ABFeatherImporter, ABPopup,
                                       SuperstructureManager, _time_it_,
                                       edit_superstructure_for_string,
                                       import_from_excel,
                                       scenario_names_from_df,
                                       scenario_replace_databases)
from ...ui.icons import qicons
from ...ui.style import header, horizontal_line, style_group_box
from ...ui.tables import (CSActivityTable, CSList, CSMethodsTable,
                          ScenarioImportTable)
from ...ui.widgets import ExcelReadDialog, ScenarioDatabaseDialog
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

        self.new_cs_button = actions.CSNew.get_QButton()
        self.duplicate_cs_button = actions.CSDuplicate.get_QButton(
            self.list_widget.currentText
        )
        self.delete_cs_button = actions.CSDelete.get_QButton(
            self.list_widget.currentText
        )
        self.rename_cs_button = actions.CSRename.get_QButton(
            self.list_widget.currentText
        )

        self.calculate_button = QtWidgets.QPushButton(qicons.calculate, "Calculate")
        self.calculation_type = QtWidgets.QComboBox()
        self.calculation_type.addItems(["Standard LCA", "Scenario LCA"])

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(header("Calculation Setup:"))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.duplicate_cs_button)
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
        reference_flow_layout.addWidget(header("Reference flows:"))
        reference_flow_layout.addWidget(self.activities_table)
        self.reference_flow_widget.setLayout(reference_flow_layout)

        # widget for the impact categories
        self.impact_categories_widget = QtWidgets.QWidget()
        impact_categories_layout = QtWidgets.QVBoxLayout()
        impact_categories_layout.addWidget(header("Impact categories:"))
        impact_categories_layout.addWidget(self.methods_table)
        self.impact_categories_widget.setLayout(impact_categories_layout)

        # splitter widget to combine the two above widgets
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.reference_flow_widget)
        self.splitter.addWidget(self.impact_categories_widget)

        self.no_setup_label = QtWidgets.QLabel(
            "To do an LCA, create a new calculation setup first by pressing 'New'."
        )
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
        signals.calculation_setup_changed.connect(self.save_cs_changes)
        self.calculation_type.currentIndexChanged.connect(self.select_calculation_type)

        # Slots
        signals.set_default_calculation_setup.connect(
            self.set_default_calculation_setup
        )
        bd.projects.current_changed.connect(self.set_default_calculation_setup)
        signals.calculation_setup_changed.connect(self.enable_calculations)
        signals.calculation_setup_selected.connect(self.select_cs)

    def save_cs_changes(self):
        name = self.list_widget.name
        if name:
            bd.calculation_setups[name] = {
                "inv": self.activities_table.to_python(),
                "ia": self.methods_table.to_python(),
            }

    @Slot(name="calculationDefault")
    def start_calculation(self):
        """Check what calculation type is selected and send the correct data signal."""

        calc_type = self.calculation_type.currentIndex()
        if calc_type == self.DEFAULT:
            # Standard LCA
            data = {
                "cs_name": self.list_widget.name,
                "calculation_type": "simple",
            }
        elif calc_type == self.SCENARIOS:
            # Scenario LCA
            data = {
                "cs_name": self.list_widget.name,
                "calculation_type": "scenario",
                "data": self.scenario_panel.scenario_dataframe(),
            }
        else:
            return

        signals.lca_calculation.emit(data)

    @Slot(name="toggleDefaultCalculation")
    def set_default_calculation_setup(self):
        self.calculation_type.setCurrentIndex(0)
        cs = None if not bd.calculation_setups else sorted(bd.calculation_setups)[0]
        signals.calculation_setup_selected.emit(cs)

    def select_cs(self, name: str):
        if not name:
            self.show_details(False)
            self.calculate_button.setEnabled(False)
        else:
            self.show_details(True)
            self.enable_calculations()

    def show_details(self, show: bool = True):
        # show/hide items from name_row
        self.rename_cs_button.setVisible(show)
        self.delete_cs_button.setVisible(show)
        self.duplicate_cs_button.setVisible(show)
        self.list_widget.setVisible(show)
        # show/hide items from calc_row
        self.calculate_button.setVisible(show)
        self.calculation_type.setVisible(show)
        # show/hide tables widgets
        self.splitter.setVisible(show)
        self.no_setup_label.setVisible(not (show))

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
        valid_cs = all(
            [self.activities_table.rowCount(), self.methods_table.rowCount()]
        )
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
        (e.g. file 1: <i>S1, S2</i> and file 2: <i>A, B</i> yields <i>S1-A, S1-B, S2-A, S2-B</i>) 
        Click <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/resources/sdf_product_combination.png"> here </a>
        for an example</p>
        <p>2. <b>Extend scenarios</b>: scenarios from file 2 extend scenarios of file 1 
        (only possible if scenario names are identical in all files, e.g. everywhere <i>S1, S2</i>).
        Click <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/resources/sdf_addition_combinations.png"> here
        </a> for an example</p> 
        """

        self.tables = []
        self._scenario_dataframe = pd.DataFrame()

        # set-up the header
        panel_header = header("Scenarios:  ")
        panel_header.setToolTip("Left click on the question mark for help")

        # set-up the control buttons
        self.table_btn = QtWidgets.QPushButton("Add scenarios", self)

        self.save_scenario = QtWidgets.QPushButton("Save to file...", self)
        self.save_scenario.setDisabled(True)

        # set-up the combination buttons

        # initiate the combine scenarios button
        self.product_choice = QtWidgets.QRadioButton("Combine scenarios", self)
        self.product_choice.setChecked(True)

        # initiate the extend scenarios button
        self.addition_choice = QtWidgets.QRadioButton("Extend scenarios", self)

        # group them and make them exclusive
        self.combine_group = QtWidgets.QButtonGroup(self)
        self.combine_group.setExclusive(True)
        self.combine_group.addButton(self.product_choice)
        self.combine_group.addButton(self.addition_choice)

        # orient them horizontally
        input_field_layout = QtWidgets.QHBoxLayout()
        input_field_layout.addWidget(self.product_choice)
        input_field_layout.addWidget(self.addition_choice)

        # add the border and hide until further notice
        self.group_box = QtWidgets.QGroupBox()
        self.group_box.setStyleSheet(style_group_box.border_title)
        self.group_box.setLayout(input_field_layout)
        self.group_box.setDisabled(True)

        # set-up the help button
        help_button = QtWidgets.QToolBar(self)
        help_button.addAction(
            qicons.question, "Left click for help on Scenarios", self.explanation
        )

        # combining all into the tool row
        tool_row = QtWidgets.QHBoxLayout()
        tool_row.addSpacing(10)
        tool_row.addWidget(panel_header)
        tool_row.addWidget(self.table_btn)
        tool_row.addWidget(self.save_scenario)
        tool_row.addWidget(self.group_box)
        tool_row.addStretch(1)
        tool_row.addWidget(QtWidgets.QLabel("More info on scenarios: "))
        tool_row.addWidget(help_button)

        # layout for the different scenario tables that can be added
        self.scenario_tables = QtWidgets.QHBoxLayout()

        # statistics at the bottom of the widget
        self.stats_widget = QtWidgets.QLabel()
        self.update_stats()

        # construct the full layout
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(tool_row)
        layout.addLayout(self.scenario_tables)
        layout.addStretch(1)
        layout.addWidget(self.stats_widget)
        self.setLayout(layout)

        self._connect_signals()

    def _connect_signals(self) -> None:
        self.table_btn.clicked.connect(self.add_table)
        self.table_btn.clicked.connect(self.can_add_table)
        self.save_scenario.clicked.connect(self.save_action)
        bd.projects.current_changed.connect(self.clear_tables)
        bd.projects.current_changed.connect(self.can_add_table)
        signals.parameter_superstructure_built.connect(
            self.handle_superstructure_signal
        )

        self.combine_group.buttonClicked.connect(self.toggle_combine_type)

    def update_stats(self) -> None:
        """Update the statistics at the bottom of the widget"""
        n_scenarios = len(self._scenario_dataframe.columns)
        n_flows = len(self._scenario_dataframe)

        stats = f"Total number of scenarios: <b>{n_scenarios}</b>  |  Total number of variable flows: <b>{n_flows}</b>"
        self.stats_widget.setText(stats)

    def toggle_combine_type(self) -> None:
        """Called by signal when the combine type is switched by the user"""
        try:
            # try to update the combined dataframe
            self.combined_dataframe()
        except:
            # revert when an exception occurs
            type = self.get_combine_type()
            if type == "product":
                self.addition_choice.setChecked(True)
            if type == "addition":
                self.product_choice.setChecked(True)

    def get_combine_type(self) -> str:
        """Return the type of combination the user wants to do"""
        if self.product_choice.isChecked():
            return "product"
        elif self.addition_choice.isChecked():
            return "addition"

    def scenario_dataframe(self) -> pd.DataFrame:
        return self._scenario_dataframe

    def scenario_names(self, idx: int) -> list:
        if idx > len(self.tables):
            return []
        return scenario_names_from_df(self.tables[idx])

    def combined_dataframe(self, skip_checks: bool = False) -> None:
        """Updates scenario dataframe to contain the combined scenarios of multiple tables."""
        # if there are no tables currently, set the dataframe to be empty
        if not self.tables:
            self._scenario_dataframe = pd.DataFrame()
            self.update_stats()
            return

        # if the tables are empty, set the dataframe to be empty
        data = [df for df in (t.dataframe for t in self.tables) if not df.empty]
        if not data:
            self._scenario_dataframe = pd.DataFrame()
            self.update_stats()
            return

        # check what kind of combination the user wants to do
        kind = self.get_combine_type()

        # combine the data using SuperstructureManager and update the dataframe
        manager = SuperstructureManager(*data)
        self._scenario_dataframe = manager.combined_data(kind, skip_checks)

        # update the stats at the bottom of the widget
        self.update_stats()

    @Slot(name="addTable")
    def add_table(self) -> None:
        """Add a new table widget to the widget and add to the list of tables"""
        new_idx = len(self.tables)
        widget = ScenarioImportWidget(new_idx, self)
        self.tables.append(widget)
        self.scenario_tables.addWidget(widget)
        self.updateGeometry()

    @Slot(int, name="removeTable")
    def remove_table(self, index: int) -> None:
        """Remove the table widget at the provided index"""
        # remove from the self.tables list and the layout
        table_widget = self.tables.pop(index)
        self.scenario_tables.removeWidget(table_widget)

        # update the other widgets with new indices
        for i, widget in enumerate(self.tables):
            widget.index = i

        # if there was data in the widget, recalculate the combined DF
        if not table_widget.dataframe.empty:
            self.combined_dataframe(skip_checks=True)

        # free up the memory
        table_widget.deleteLater()

        # update save_scenario button
        if not self.tables:
            self.save_scenario.setDisabled(True)
        self.updateGeometry()

    @Slot(name="clearTables")
    def clear_tables(self) -> None:
        """Clear all scenario tables in certain cases (eg. project change)."""
        for w in self.tables:
            self.scenario_tables.removeWidget(w)
            w.deleteLater()
        self.tables = []
        self.save_scenario.setDisabled(True)
        self.updateGeometry()
        self.combined_dataframe()

    def updateGeometry(self):
        self.group_box.setDisabled(len(self.tables) <= 1)
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

    @Slot(int, name="SaveScenarioDataframe")
    def save_action(self) -> None:
        """Creates and saves to file (.xlsx, or .csv) the scenario dataframe after the loaded scenarios have been
        merged. Will not contain duplicates. Will not contain self-referential technosphere flows.

        Triggered by a signal from ScenarioImportPanel save button, uses a dummy input argument.
        """
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Choose location to save the scenario file",
            filter="Excel (*.xlsx *.xls);; CSV (*.csv)",
        )
        print("Saving scenario dataframe to file: ", filepath)
        scenarios = self._scenario_dataframe.columns.difference(
            ["input", "output", "flow"]
        )
        superstructure = SUPERSTRUCTURE.tolist()
        cols = superstructure + scenarios.tolist()

        savedf = pd.DataFrame(index=self._scenario_dataframe.index, columns=cols)
        for table in self.tables:
            indices = savedf.index.intersection(table.scenario_df.index)
            savedf.loc[indices, superstructure] = table.scenario_df.loc[
                indices, superstructure
            ]
            savedf.loc[indices, scenarios] = self._scenario_dataframe.loc[
                indices, scenarios
            ]
        if filepath.endswith(".xlsx") or filepath.endswith(".xls"):
            savedf.to_excel(filepath, index=False)
            return
        elif not filepath.endswith(".csv"):
            filepath += ".csv"
        savedf.to_csv(filepath, index=False, sep=";")

    def save_button(self, visible: bool):
        self.save_scenario.setDisabled(not visible)
        self.show()
        self.updateGeometry()


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
        layout.addStretch(1)
        self.setLayout(layout)
        self._connect_signals()

    def _connect_signals(self):
        self.load_btn.clicked.connect(self.load_action)
        parent = self.parent()
        if parent and isinstance(parent, ScenarioImportPanel):
            self.remove_btn.clicked.connect(lambda: parent.remove_table(self.index))
            self.remove_btn.clicked.connect(parent.can_add_table)

    @_time_it_
    @Slot(name="loadScenarioFile")
    def load_action(self) -> None:
        dialog = ExcelReadDialog(self)
        if dialog.exec_() == ExcelReadDialog.Accepted:

            try:
                path = dialog.path
                idx = dialog.import_sheet.currentIndex()
                file_type_suffix = dialog.path.suffix
                separator = dialog.field_separator.currentData()
                log.debug("separator == '{}'".format(separator))
                QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
                log.info("Loading Scenario file. This may take a while for large files")
                # Try and read as a superstructure file
                # Choose a different routine for reading the file dependent on file type
                if file_type_suffix == ".feather":
                    df = ABFeatherImporter.read_file(path)
                elif file_type_suffix.startswith(".xls"):
                    df = import_from_excel(path, idx)
                else:
                    df = ABCSVImporter.read_file(path, separator=separator)
                # Read in the file as a scenario flow table if the file is arranged as one
                if len(df.columns.intersection(SUPERSTRUCTURE)) >= 12:
                    if df is None:
                        QtWidgets.QApplication.restoreOverrideCursor()
                        return
                    self.sync_superstructure(df)
                # Read the file as a parameter scenario file if it is correspondingly arranged
                elif len(df.columns.intersection({"Name", "Group"})) == 2:
                    # Try and read as parameter scenario file.
                    log.info(
                        "Superstructure: Attempting to read as parameter scenario file."
                    )
                    include_default = True
                    if "default" not in df.columns:
                        query = QtWidgets.QMessageBox.question(
                            self,
                            "Default column not found",
                            "Attempt to load and include the 'default' scenario column?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No,
                        )
                        if query == QtWidgets.QMessageBox.No:
                            include_default = False
                    signals.parameter_scenario_sync.emit(
                        self.index, df, include_default
                    )
                else:
                    # this is a wrong file type
                    msg = (
                        "The Activity-Browser is attempting to import a scenario file.<p>During the attempted import"
                        " another file type was detected. Please check the file type of the attempted import, if it is"
                        " a scenario file make sure it contains a valid format.</p>"
                        "<p>A flow exchange scenario file requires the following headers:<br>"
                        + edit_superstructure_for_string(sep=", ", fhighlight='"')
                        + "</p>"
                        "<p>A parameter scenario file requires the following:<br>"
                        + edit_superstructure_for_string(
                            ["name", "group"], sep=", ", fhighlight='"'
                        )
                        + "</p>"
                    )
                    critical = ABPopup.abCritical(
                        "Wrong file type", msg, QtWidgets.QPushButton("Cancel")
                    )
                    QtWidgets.QApplication.restoreOverrideCursor()
                    critical.exec_()
                    return
            except CriticalScenarioExtensionError as e:
                # Triggered when combining different scenario files by extension leads to no scenario columns
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except ScenarioDatabaseNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except ScenarioExchangeNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except ImportCanceledError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except ScenarioExchangeDataNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except UnalignableScenarioColumnsWarning as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            self.scenario_name.setText(path.name)
            self.scenario_name.setToolTip(path.name)
            self._parent.save_button(True)
            QtWidgets.QApplication.restoreOverrideCursor()

    @_time_it_
    def sync_superstructure(self, df: pd.DataFrame) -> None:
        """synchronizes the contents of either a single, or multiple scenario files to create a single scenario
        dataframe"""
        # TODO: Move the 'scenario_df' into the model itself.
        QtWidgets.QApplication.restoreOverrideCursor()
        df = self.scenario_db_check(df)
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        df = SuperstructureManager.fill_empty_process_keys_in_exchanges(df)
        SuperstructureManager.verify_scenario_process_keys(df)
        df = SuperstructureManager.check_duplicates(df)
        # TODO add the key checks here and field checks here.
        # If we've cancelled the import then we don't want to load the dataframe
        if df.empty:
            return
        self.scenario_df = df
        cols = scenario_names_from_df(self.scenario_df)
        self.table.model.sync(cols)
        self._parent.combined_dataframe()

    @_time_it_
    def scenario_db_check(self, df: pd.DataFrame) -> pd.DataFrame:
        dbs = set(df.loc[:, "from database"]).union(set(df.loc[:, "to database"]))
        unlinkable = dbs.difference(bd.databases)
        db_lst = list(bd.databases)
        relink = []
        for db in unlinkable:
            relink.append((db, db_lst))
        # check for databases in the scenario dataframe that cannot be linked to
        if unlinkable:
            dialog = ScenarioDatabaseDialog.construct_dialog(self._parent, relink)
            if dialog.exec_() == dialog.Accepted:
                # TODO On update to bw2.5 this should be changed to use the bw2data.utils.get_node method
                return scenario_replace_databases(df, dialog.relink)
                # generate the required dialog
        return df

    @property
    def dataframe(self) -> pd.DataFrame:
        if self.scenario_df.empty:
            log.debug("No data in scenario table {}, skipping".format(self.index + 1))
        return self.scenario_df
