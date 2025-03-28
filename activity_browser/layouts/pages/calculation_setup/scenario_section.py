from logging import getLogger
from pathlib import Path

from qtpy import QtWidgets
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd

from activity_browser import signals
from activity_browser.ui import icons, widgets
from activity_browser.bwutils import superstructure as ss
from activity_browser.bwutils import errors

log = getLogger(__name__)


class ScenarioSection(QtWidgets.QWidget):
    max_tables = 5

    """Special kind of QWidget that contains one or more tables side by side."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tables = []
        self._scenario_dataframe = pd.DataFrame()

        # set up the control buttons
        self.table_btn = QtWidgets.QPushButton("Add scenarios...", self)

        self.save_scenario = QtWidgets.QPushButton("Save to file...", self)
        self.save_scenario.setDisabled(True)

        # set up the combination buttons

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
        input_field_layout.setContentsMargins(0, 0, 0, 0)
        input_field_layout.addWidget(self.product_choice)
        input_field_layout.addWidget(self.addition_choice)

        # add the border and hide until further notice
        self.group_box = QtWidgets.QGroupBox()
        self.group_box.setLayout(input_field_layout)
        self.group_box.setDisabled(True)

        # combining all into the tool row
        tool_row = QtWidgets.QHBoxLayout()
        tool_row.setContentsMargins(0, 0, 0, 0)
        tool_row.addSpacing(10)

        tool_row.addWidget(widgets.ABLabel.demiBold("  Scenarios:", self))
        tool_row.addStretch()
        tool_row.addWidget(self.table_btn)
        tool_row.addWidget(self.save_scenario)
        tool_row.addWidget(self.group_box)

        # layout for the different scenario tables that can be added
        self.scenario_tables = QtWidgets.QHBoxLayout()

        # statistics at the bottom of the widget
        self.stats_widget = QtWidgets.QLabel()
        self.update_stats()

        # construct the full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addLayout(tool_row)
        layout.addLayout(self.scenario_tables)
        layout.addStretch(1)
        layout.addWidget(self.stats_widget)
        self.setLayout(layout)

        self.connect_signals()

    def connect_signals(self) -> None:
        signals.project.changed.connect(self.clear_tables)
        signals.project.changed.connect(self.can_add_table)
        signals.parameter_superstructure_built.connect(self.handle_superstructure_signal)

        self.table_btn.clicked.connect(self.add_table)
        self.table_btn.clicked.connect(self.can_add_table)
        self.save_scenario.clicked.connect(self.save_action)
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
        return ss.scenario_names_from_df(self.tables[idx])

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
        manager = ss.SuperstructureManager(*data)
        self._scenario_dataframe = manager.combined_data(kind, skip_checks)

        # update the stats at the bottom of the widget
        self.update_stats()

    def add_table(self) -> None:
        """Add a new table widget to the widget and add to the list of tables"""
        new_idx = len(self.tables)
        widget = ScenarioImportWidget(new_idx, self)
        self.tables.append(widget)
        self.scenario_tables.addWidget(widget)
        self.updateGeometry()

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

    def can_add_table(self) -> None:
        """Use this to set a hardcoded limit on the amount of scenario tables
        a user can add.
        """
        self.table_btn.setEnabled(len(self.tables) < self.max_tables)

    def handle_superstructure_signal(self, table_idx: int, df: pd.DataFrame) -> None:
        table = self.tables[table_idx]
        table.sync_superstructure(df)

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
        superstructure = ss.SUPERSTRUCTURE.tolist()
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
        self.load_btn = QtWidgets.QPushButton(icons.qicons.import_db, "Load")
        self.load_btn.setToolTip("Load (new) data for this scenario table")
        self.remove_btn = QtWidgets.QPushButton(icons.qicons.delete, "Delete")
        self.remove_btn.setToolTip("Remove this scenario table")
        self.view = widgets.ABTreeView(self)
        self.model = widgets.ABItemModel(self)
        self.view.setModel(self.model)
        self.scenario_df = pd.DataFrame(columns=ss.SUPERSTRUCTURE)

        layout = QtWidgets.QVBoxLayout()

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.scenario_name)
        row.addWidget(self.load_btn)
        row.addStretch(1)
        row.addWidget(self.remove_btn)

        layout.addLayout(row)
        layout.addWidget(self.view)
        layout.addStretch(1)
        self.setLayout(layout)
        self.connect_signals()

    def connect_signals(self):
        self.load_btn.clicked.connect(self.load_action)
        parent = self.parent()
        if parent and isinstance(parent, ScenarioSection):
            self.remove_btn.clicked.connect(lambda: parent.remove_table(self.index))
            self.remove_btn.clicked.connect(parent.can_add_table)

    def load_action(self) -> None:
        dialog = ExcelReadDialog(self)
        if dialog.exec_() == ExcelReadDialog.DialogCode.Accepted:

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
                    df = ss.ABFeatherImporter.read_file(path)
                elif file_type_suffix.startswith(".xls"):
                    df = ss.import_from_excel(path, idx)
                else:
                    df = ss.ABCSVImporter.read_file(path, separator=separator)
                # Read in the file as a scenario flow table if the file is arranged as one
                if len(df.columns.intersection(ss.SUPERSTRUCTURE)) >= 12:
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

                    if not df["Group"].dtype == object:
                        df["Group"] = df["Group"].astype(str)

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
                        + ss.edit_superstructure_for_string(sep=", ", fhighlight='"')
                        + "</p>"
                        "<p>A parameter scenario file requires the following:<br>"
                        + ss.edit_superstructure_for_string(
                            ["name", "group"], sep=", ", fhighlight='"'
                        )
                        + "</p>"
                    )
                    critical = ss.ABPopup.abCritical(
                        "Wrong file type", msg, QtWidgets.QPushButton("Cancel")
                    )
                    QtWidgets.QApplication.restoreOverrideCursor()
                    critical.exec_()
                    return
            except errors.CriticalScenarioExtensionError as e:
                # Triggered when combining different scenario files by extension leads to no scenario columns
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except errors.ScenarioDatabaseNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except errors.ScenarioExchangeNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except errors.ImportCanceledError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except errors.ScenarioExchangeDataNotFoundError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            except errors.UnalignableScenarioColumnsWarning as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                return
            self.scenario_name.setText(path.name)
            self.scenario_name.setToolTip(path.name)
            self._parent.save_button(True)
            QtWidgets.QApplication.restoreOverrideCursor()

    def sync_superstructure(self, df: pd.DataFrame) -> None:
        """synchronizes the contents of either a single, or multiple scenario files to create a single scenario
        dataframe"""
        QtWidgets.QApplication.restoreOverrideCursor()
        df = self.scenario_db_check(df)
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        df = ss.SuperstructureManager.fill_empty_process_keys_in_exchanges(df)
        ss.SuperstructureManager.verify_scenario_process_keys(df)
        df = ss.SuperstructureManager.check_duplicates(df)
        # If we've cancelled the import then we don't want to load the dataframe
        if df.empty:
            return
        self.scenario_df = df
        cols = ss.scenario_names_from_df(self.scenario_df)
        self.model.setDataFrame(pd.DataFrame(cols, columns=["Scenarios"]))
        self._parent.combined_dataframe()

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
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # TODO On update to bw2.5 this should be changed to use the bw2data.utils.get_node method
                return ss.scenario_replace_databases(df, dialog.relink)
                # generate the required dialog
        return df

    @property
    def dataframe(self) -> pd.DataFrame:
        if self.scenario_df.empty:
            log.debug("No data in scenario table {}, skipping".format(self.index + 1))
        return self.scenario_df


class ExcelReadDialog(QtWidgets.QDialog):
    SUFFIXES = {
        ".xls",
        ".xlsx",
        ".bz2",
        ".zip",
        ".gz",
        ".xz",
        ".tar",
        ".csv",
        ".feather",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select file to read")

        self.path_layout = QtWidgets.QGridLayout()
        self.path = None
        self.path_line = QtWidgets.QLineEdit()
        self.path_line.setReadOnly(True)
        self.path_line.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.path_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        self.path_layout.addWidget(self.path_line, 0, 1, 1, 2)
        self.path_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        self.path = QtWidgets.QWidget()
        self.path.setLayout(self.path_layout)

        self.excel_option = QtWidgets.QHBoxLayout()
        self.import_sheet = QtWidgets.QComboBox()
        self.import_sheet.addItems(["-----"])
        self.import_sheet.setEnabled(True)
        self.excel_option.addWidget(
            QtWidgets.QLabel("Excel sheet name")
        )  # , 0, 0, 1, 1)
        self.excel_option.addWidget(self.import_sheet)  # , 0, 1, 2, 1)
        self.excel_sheet = QtWidgets.QWidget()
        self.excel_sheet.setLayout(self.excel_option)
        self.excel_sheet.setVisible(False)

        self.csv_option = QtWidgets.QHBoxLayout()
        self.field_separator = QtWidgets.QComboBox()
        for l, s in {";": ";", ",": ",", "tab": "\t"}.items():
            self.field_separator.addItem(l, s)
        self.field_separator.setEnabled(True)
        self.csv_option.addWidget(
            QtWidgets.QLabel("Separator for csv")
        )  # , 0, 0, 1, 1)
        self.csv_option.addWidget(self.field_separator)  # , 0, 1, 2, 1)
        self.csv_separator = QtWidgets.QWidget()
        self.csv_separator.setLayout(self.csv_option)
        self.csv_separator.setVisible(False)

        self.complete = False

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.complete)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        grid = QtWidgets.QVBoxLayout()
        grid.addWidget(self.path)
        grid.addWidget(self.excel_sheet)
        grid.addWidget(self.csv_separator)

        input_box = QtWidgets.QGroupBox(self)
        input_box.setLayout(grid)
        layout.addWidget(input_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption="Select scenario template file",
            filter="Excel (*.xlsx);; feather (*.feather);; CSV and Archived (*.csv *.zip *.tar *.bz2 *.gz *.xz);; All Files (*.*)",
            selectedFilter="All Files (*.*)",
        )
        if path:
            self.path_line.setText(path)

    def update_combobox(self, file_path) -> None:
        self.import_sheet.blockSignals(True)
        self.import_sheet.clear()
        names = ss.get_sheet_names(file_path)
        self.import_sheet.addItems(names)
        self.import_sheet.blockSignals(False)

    def changed(self) -> None:
        """Determine if selected path is valid."""
        self.path = Path(self.path_line.text())
        self.complete = all(
            [self.path.exists(), self.path.is_file(), self.path.suffix in self.SUFFIXES]
        )
        if self.complete and self.path.suffix.startswith(".xls"):
            self.update_combobox(self.path)
            self.excel_sheet.setVisible(self.import_sheet.count() > 0)
            self.csv_separator.setVisible(False)
        elif self.complete and self.path.suffix in {
            ".csv",
            ".zip",
            ".tar",
            ".bz2",
            ".gz",
            ".xz",
        }:
            self.csv_separator.setVisible(True)
            self.excel_sheet.setVisible(False)
        else:
            self.csv_separator.setVisible(False)
            self.excel_sheet.setVisible(False)
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.complete)


class ScenarioDatabaseDialog(QtWidgets.QDialog):
    """
    Displays the possible databases for relinking the exchanges for a given activity
    """

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Linking scenario databases")

        self.label = QtWidgets.QLabel(
            "The following database(s) in the scenario file cannot be found in your project.\n\n"
            "Please indicate the corresponding database(s), or cancel the import if this is not"
            " possible. (Warning: this process may take a few minutes for large scenario files)"
        )

        self.label_choices = []
        self.grid_box = QtWidgets.QGroupBox("DatabasesPane:")
        self.grid = QtWidgets.QGridLayout()
        self.grid_box.setLayout(self.grid)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.grid_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def relink(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.

        Only returns key/value pairs if they differ.
        """
        return {
            label.text(): combo.currentText()
            for label, combo in self.label_choices
            if label.text() != combo.currentText()
        }

    @classmethod
    def construct_dialog(cls, parent: QtWidgets.QWidget = None, options: list = None) -> "ScenarioDatabaseDialog":
        obj = cls(parent)
        # Start at 1 because row 0 is taken up by the db_label
        for i, item in enumerate(options):
            label = QtWidgets.QLabel(item[0])
            combo = QtWidgets.QComboBox()
            combo.addItems(item[1])
            combo.setCurrentIndex(0)
            obj.label_choices.append((label, combo))
            obj.grid.addWidget(label, i, 0, 1, 2)
            obj.grid.addWidget(combo, i, 2, 1, 2)
        obj.updateGeometry()
        return obj

