from loguru import logger
from pathlib import Path

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd
from activity_browser.bwutils import superstructure as ss
from activity_browser.bwutils.superstructure import scenario_templates as scen_tpl

from activity_browser import app
from activity_browser.bwutils import calculation_setup as cs_helpers
from activity_browser.bwutils.superstructure import inclusion as scen_inc
from activity_browser.ui import icons, widgets, core, delegates
from activity_browser.ui.icons import qicons


class ScenarioSection(QtWidgets.QWidget):
    max_tables = 5

    """Special kind of QWidget that contains one or more tables side by side."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tables = []
        self._scenario_dataframe = pd.DataFrame()
        self._included: list[str] = []
        self._axes: list[list[str]] = []
        self._mode: str | None = None
        self._last_inclusion_mismatch = False
        self._datapackage_loaded_this_session = False

        # set up the control buttons
        self.table_btn = QtWidgets.QPushButton("Add scenarios...", self)
        self.get_template_btn = QtWidgets.QPushButton("Template...", self)
        self.get_template_btn.setToolTip(
            "Download a parameter- or flow-scenario starter file (.xlsx or .csv)"
        )
        self.save_scenario = QtWidgets.QPushButton("Save...", self)
        self.save_scenario.setToolTip(
            "Save the loaded scenarios to a flow-scenarios file"
        )
        self.save_scenario.setDisabled(True)

        self.help_btn = QtWidgets.QToolButton(self)
        self.help_btn.setIcon(qicons.question)
        self.help_btn.setAutoRaise(True)
        self.help_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.help_btn.setToolTip("Help: scenario modeling in Activity Browser")

        # set up the combination buttons

        # initiate the combine scenarios button
        self.product_choice = QtWidgets.QRadioButton("Combine scenarios", self)
        self.product_choice.setChecked(True)
        self.product_choice.setToolTip(
            "Build all or selected combinations of scenarios from the loaded files"
        )

        # initiate the extend scenarios button
        self.addition_choice = QtWidgets.QRadioButton("Extend scenarios", self)
        self.addition_choice.setToolTip(
            "Extend files on shared scenario names (only works for matching scenario names across files)"
        )

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
        tool_row.addWidget(self.get_template_btn)
        tool_row.addWidget(self.save_scenario)
        tool_row.addWidget(self.group_box)
        tool_row.addWidget(self.help_btn)

        # layout for the different scenario tables that can be added
        self.scenario_tables = QtWidgets.QHBoxLayout()
        self.tables_host = QtWidgets.QWidget(self)
        self.tables_host.setLayout(self.scenario_tables)

        self.combinations_panel = ScenarioCombinationsPanel(self)
        self.combinations_panel.hide()

        content_row = QtWidgets.QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.addWidget(self.tables_host, stretch=3)
        content_row.addWidget(self.combinations_panel, stretch=2)

        # statistics at the bottom of the widget
        self.stats_widget = QtWidgets.QLabel()
        self.update_stats()

        self.sdf_panel = QtWidgets.QWidget(self)
        sdf_layout = QtWidgets.QVBoxLayout()
        sdf_layout.setContentsMargins(0, 0, 0, 0)
        sdf_layout.addLayout(tool_row)
        sdf_layout.addLayout(content_row)
        sdf_layout.addStretch(1)
        sdf_layout.addWidget(self.stats_widget)
        self.sdf_panel.setLayout(sdf_layout)

        self.datapackage_panel = DatapackageScenarioPanel(self)
        self.datapackage_panel.hide()

        self.sdf_choice = QtWidgets.QRadioButton("SDF", self)
        self.sdf_choice.setToolTip("Scenario difference files")
        self.sdf_choice.setChecked(True)
        self.datapackage_choice = QtWidgets.QRadioButton("Datapackage", self)
        self.datapackage_choice.setToolTip("One scenario datapackage")
        self.input_group = QtWidgets.QButtonGroup(self)
        self.input_group.setExclusive(True)
        self.input_group.addButton(self.sdf_choice)
        self.input_group.addButton(self.datapackage_choice)

        input_row = QtWidgets.QHBoxLayout()
        input_row.setContentsMargins(10, 0, 0, 0)
        input_row.addWidget(widgets.ABLabel.demiBold("Scenario input:", self))
        input_row.addWidget(self.sdf_choice)
        input_row.addWidget(self.datapackage_choice)
        input_row.addStretch(1)

        # construct the full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 10, 0)
        layout.addLayout(input_row)
        layout.addWidget(self.sdf_panel)
        layout.addWidget(self.datapackage_panel)
        self.setLayout(layout)

        self.connect_signals()

    def connect_signals(self) -> None:
        app.signals.project.changed.connect(self.clear_tables)
        app.signals.project.changed.connect(self.can_add_table)

        self.table_btn.clicked.connect(self.add_table)
        self.table_btn.clicked.connect(self.can_add_table)
        self.get_template_btn.clicked.connect(self.get_template_action)
        self.save_scenario.clicked.connect(self.save_action)
        self.help_btn.clicked.connect(self.show_scenarios_help)
        self.combine_group.buttonClicked.connect(self.toggle_combine_type)
        self.input_group.buttonClicked.connect(self._on_scenario_input_clicked)
        app.signals.project.changed.connect(self._reset_datapackage_on_project_change)

    def get_template_action(self) -> None:
        """Save a parameter- or flow-scenario starter template chosen by the user."""
        dialog = GetScenarioTemplateDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        kind, fmt = dialog.selection()
        default_name = (
            f"parameter-scenarios.{fmt}" if kind == "parameter" else f"flow-scenarios.{fmt}"
        )
        if fmt == "xlsx":
            file_filter = "Excel (*.xlsx)"
        else:
            file_filter = "CSV (*.csv)"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Save scenario template",
            dir=str(Path.home() / default_name),
            filter=file_filter,
        )
        if not path:
            return
        dest = Path(path)
        try:
            if kind == "flow" or not scen_tpl.project_has_parameters():
                scen_tpl.copy_scenario_template(kind, fmt, dest)
            else:
                if dest.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
                    dest = dest.with_suffix(f".{fmt}")
                scen_tpl.write_parameter_template(dest)
        except Exception:
            logger.exception("Failed to write scenario template to {}", dest)
            QtWidgets.QMessageBox.critical(
                self,
                "Could not save template",
                f"Failed to save the scenario template to:\n{dest}",
            )

    def show_scenarios_help(self) -> None:
        ScenariosHelpDialog(self).exec_()

    def update_stats(self) -> None:
        """Update the statistics at the bottom of the widget"""
        n_total = len(self._scenario_dataframe.columns)
        n_selected = len(self._included) if n_total else 0

        stats = (
            f"Selected scenarios: <b>{n_selected}</b> / <b>{n_total}</b>"
            f"  |  Total number of variable flows: <b>{len(self._scenario_dataframe)}</b>"
        )
        self.stats_widget.setText(stats)

    def toggle_combine_type(self) -> None:
        """Rebuild after Combine/Extend switch; restore prior mode on failure."""
        # Radio already shows the new mode; _mode still holds the previous one.
        previous = self._mode
        try:
            self.combined_dataframe()
        except Exception:
            logger.exception("Failed to switch scenario combine mode")
            if previous is None:
                previous = (
                    scen_inc.MODE_ADDITION
                    if self.get_combine_type() == scen_inc.MODE_PRODUCT
                    else scen_inc.MODE_PRODUCT
                )
            self._restore_combine_mode(previous)

    def _restore_combine_mode(self, mode: str) -> None:
        """Put radios back without re-entering toggle_combine_type."""
        self.combine_group.blockSignals(True)
        try:
            if mode == scen_inc.MODE_PRODUCT:
                self.product_choice.setChecked(True)
            else:
                self.addition_choice.setChecked(True)
        finally:
            self.combine_group.blockSignals(False)

    def get_combine_type(self) -> str:
        """Return the type of combination the user wants to do"""
        if self.product_choice.isChecked():
            return scen_inc.MODE_PRODUCT
        return scen_inc.MODE_ADDITION

    def scenario_dataframe(self) -> pd.DataFrame:
        return cs_helpers.filter_scenario_dataframe(
            self._scenario_dataframe, self._included
        )

    def cs_name(self) -> str | None:
        parent = self.parent()
        return getattr(parent, "calculation_setup_name", None)

    def current_axes(self) -> list[list[str]]:
        return [
            ss.scenario_names_from_df(table.dataframe)
            for table in self.tables
            if not table.dataframe.empty
        ]

    def _set_included(self, included: list[str]) -> None:
        self._included = list(included)
        self.refresh_inclusion_ui()
        self.persist_inclusion()

    def refresh_inclusion_ui(self) -> None:
        mode = self.get_combine_type()
        if self._axes:
            flags = scen_inc.derive_file_flags(self._included, self._axes, mode)
            data_tables = [t for t in self.tables if not t.dataframe.empty]
            for table, file_flags in zip(data_tables, flags):
                table.sync_inclusion_flags(file_flags)
        self.sync_combinations_panel()
        self.update_stats()

    def sync_combinations_panel(self) -> None:
        show = (
            self.get_combine_type() == scen_inc.MODE_PRODUCT
            and len(self._axes) >= 2
        )
        self.combinations_panel.setVisible(show)
        if show:
            included = set(self._included)
            self.combinations_panel.set_combinations(
                [
                    (name, name in included)
                    for name in scen_inc.product_universe(self._axes)
                ]
            )

    def set_combination_included(self, name: str, active: bool) -> None:
        if active == (name in self._included):
            return
        self._set_included(
            scen_inc.toggle_combination(
                self._included, name, self._axes, self.get_combine_type()
            )
        )

    def select_all_combinations(self) -> None:
        if self.get_combine_type() != scen_inc.MODE_PRODUCT or len(self._axes) < 2:
            return
        self._set_included(scen_inc.all_included(self._axes, scen_inc.MODE_PRODUCT))

    def select_none_combinations(self) -> None:
        if self.get_combine_type() != scen_inc.MODE_PRODUCT or len(self._axes) < 2:
            return
        self._set_included([])

    def set_name_included(self, file_index: int, name: str, active: bool) -> None:
        mode = self.get_combine_type()
        op = scen_inc.check_name if active else scen_inc.uncheck_name
        self._set_included(op(self._included, self._axes, file_index, name, mode))

    def persist_inclusion(self) -> None:
        name = self.cs_name()
        if not name:
            return
        tables = [
            t for t in self.tables if getattr(t, "file_path", None) is not None
        ]
        paths = [str(t.file_path) for t in tables]
        sheets = [getattr(t, "sheet_index", None) for t in tables]
        if not paths or not self._axes:
            return
        cs_helpers.set_scenario_persistence(
            name,
            paths=paths,
            sheets=sheets,
            combine=self.get_combine_type(),
            included=self._included,
            axes=self._axes,
        )

    def reconcile_inclusion_after_combine(self) -> bool:
        """Reconcile S after combine. Returns True if axes mismatched vs prior S."""
        new_axes = self.current_axes()
        mode = self.get_combine_type()
        mode_changed = self._mode is not None and self._mode != mode
        mismatched = False
        if mode_changed or not self._axes:
            included = scen_inc.all_included(new_axes, mode)
        else:
            result = scen_inc.reconcile_included(
                self._included, self._axes, new_axes, mode
            )
            included = result.included
            mismatched = result.mismatched
        self._axes = [list(a) for a in new_axes]
        self._mode = mode
        self._last_inclusion_mismatch = mismatched
        self._set_included(included)
        return mismatched

    def uses_datapackage(self) -> bool:
        return self.datapackage_choice.isChecked()

    def scenario_datapackage(self) -> dict:
        """Path and included scenario names currently shown on the datapackage side."""
        return {
            "path": self.datapackage_panel.path(),
            "included": self.datapackage_panel.included_names(),
        }

    def load_persisted_scenarios(self) -> None:
        """Restore the saved scenario input and load only that side."""
        name = self.cs_name()
        kind = cs_helpers.INPUT_SDF
        if name and name in bd.calculation_setups:
            kind = cs_helpers.scenario_input_kind(bd.calculation_setups[name])
        self._set_input_kind_ui(kind)
        self.load_active_scenario_input(force=False)

    def load_active_scenario_input(self, *, force: bool) -> None:
        """Load the visible side from the calculation setup.

        Entering Scenario mode leaves a side that is already loaded. Switching
        the radio reloads that side from the calculation setup.
        """
        if self.uses_datapackage():
            if self._datapackage_loaded_this_session and not force:
                return
            self._load_datapackage_side()
            self._datapackage_loaded_this_session = True
            return
        if (
            not force
            and self.tables
            and any(not table.dataframe.empty for table in self.tables)
        ):
            return
        if force:
            self.clear_tables()
        self._load_sdf_from_cs()

    def _set_input_kind_ui(self, kind: str) -> None:
        self.input_group.blockSignals(True)
        try:
            if kind == cs_helpers.INPUT_DATAPACKAGE:
                self.datapackage_choice.setChecked(True)
            else:
                self.sdf_choice.setChecked(True)
            self._apply_input_visibility()
        finally:
            self.input_group.blockSignals(False)

    def _apply_input_visibility(self) -> None:
        datapackage = self.uses_datapackage()
        self.sdf_panel.setVisible(not datapackage)
        self.datapackage_panel.setVisible(datapackage)

    def _on_scenario_input_clicked(self) -> None:
        kind = (
            cs_helpers.INPUT_DATAPACKAGE
            if self.uses_datapackage()
            else cs_helpers.INPUT_SDF
        )
        name = self.cs_name()
        if name and name in bd.calculation_setups:
            cs_helpers.set_scenario_input(name, kind)
        self._apply_input_visibility()
        self.load_active_scenario_input(force=True)

    def _reset_datapackage_on_project_change(self) -> None:
        self._datapackage_loaded_this_session = False
        self.datapackage_panel.clear()
        self._set_input_kind_ui(cs_helpers.INPUT_SDF)

    def use_datapackage_path(self, path: str) -> None:
        """Attach one scenario datapackage and select every scenario name."""
        path = (path or "").strip()
        name = self.cs_name()
        if name and name in bd.calculation_setups:
            cs_helpers.set_scenario_input(name, cs_helpers.INPUT_DATAPACKAGE)
        if not path:
            self._clear_datapackage_side()
            return
        self._read_datapackage_into_panel(path, included=None)

    def on_datapackage_inclusion_changed(self) -> None:
        path = self.datapackage_panel.path()
        name = self.cs_name()
        if not path or not name or name not in bd.calculation_setups:
            self.datapackage_panel.update_count()
            return
        cs_helpers.set_scenario_datapackage_persistence(
            name, path, self.datapackage_panel.included_names()
        )
        self.datapackage_panel.update_count()

    def _load_datapackage_side(self) -> None:
        name = self.cs_name()
        if not name or name not in bd.calculation_setups:
            self.datapackage_panel.clear()
            return
        saved = cs_helpers.get_scenario_datapackage(bd.calculation_setups[name])
        if not saved:
            self.datapackage_panel.clear()
            return
        path = saved[cs_helpers.SCENARIO_DATAPACKAGE_PATH]
        if not Path(path).exists():
            self._warn_and_clear_datapackage(path, missing=True)
            return
        self._read_datapackage_into_panel(
            path, included=saved[cs_helpers.SCENARIO_DATAPACKAGE_INCLUDED]
        )

    def _read_datapackage_into_panel(self, path: str, included: list[str] | None) -> None:
        from activity_browser.bwutils.scenario_datapackage import (
            ScenarioDatapackageError,
            read_scenario_datapackage,
        )

        try:
            contents = read_scenario_datapackage(path)
        except ScenarioDatapackageError:
            self._warn_and_clear_datapackage(path, missing=not Path(path).exists())
            return
        if contents.used_fallback:
            QtWidgets.QMessageBox.warning(
                self,
                "Scenario names",
                "Scenario names in this datapackage are missing or do not match "
                "the scenario columns.\n\nUsing Scenario 0, Scenario 1, and so on.",
            )
        chosen, mismatched = cs_helpers.reconcile_datapackage_inclusion(
            included, contents.names
        )
        if mismatched:
            QtWidgets.QMessageBox.warning(
                self,
                "Scenario selection reset",
                "Saved scenario names no longer match this datapackage. "
                "All scenarios were selected again.",
            )
        name = self.cs_name()
        if name and name in bd.calculation_setups:
            cs_helpers.set_scenario_datapackage_persistence(name, path, chosen)
        self.datapackage_panel.show_scenarios(path, contents.names, chosen)

    def _warn_and_clear_datapackage(self, path: str, *, missing: bool) -> None:
        if missing:
            text = (
                "The scenario datapackage could not be found:\n"
                f"{path}\n\n"
                "This side was cleared. Scenario difference files are unchanged."
            )
        else:
            text = (
                "The scenario datapackage could not be read:\n"
                f"{path}\n\n"
                "This side was cleared. Scenario difference files are unchanged."
            )
        QtWidgets.QMessageBox.warning(self, "Scenario datapackage", text)
        self._clear_datapackage_side()

    def _clear_datapackage_side(self) -> None:
        name = self.cs_name()
        if name and name in bd.calculation_setups:
            cs_helpers.clear_scenario_datapackage_persistence(name)
        self.datapackage_panel.clear()

    def _load_sdf_from_cs(self) -> None:
        """Reload scenario difference files from the CS."""
        name = self.cs_name()
        if not name or name not in bd.calculation_setups:
            return
        saved = cs_helpers.get_scenario_persistence(bd.calculation_setups[name])
        if not saved:
            return

        paths = [Path(p) for p in saved[cs_helpers.SCENARIO_PATHS]]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            QtWidgets.QMessageBox.warning(
                self,
                "Scenario files not found",
                "One or more saved scenario files could not be found:\n"
                + "\n".join(str(p) for p in missing)
                + "\n\nLoad scenario files from scratch.",
            )
            cs_helpers.clear_scenario_persistence(name)
            self.clear_tables()
            return

        progress = QtWidgets.QProgressDialog(
            "Loading scenarios…", None, 0, 0, self
        )
        progress.setWindowTitle("Scenarios")
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        QtWidgets.QApplication.processEvents()

        try:
            combine = saved[cs_helpers.SCENARIO_COMBINE]
            if combine == scen_inc.MODE_ADDITION:
                self.addition_choice.setChecked(True)
            else:
                self.product_choice.setChecked(True)

            sheets = saved.get(cs_helpers.SCENARIO_SHEETS) or [None] * len(paths)
            if len(sheets) < len(paths):
                sheets = list(sheets) + [None] * (len(paths) - len(sheets))

            for path, sheet in zip(paths, sheets):
                self.add_table()
                widget = self.tables[-1]
                ok = widget.load_from_path(
                    path, sheet_index=sheet, combine=False, quiet=True
                )
                if not ok:
                    raise RuntimeError(
                        f"Failed to load scenario file (no valid scenario sheet found): {path}"
                    )

            # Seed prior S/axes so reconcile can restore or detect mismatch.
            self._included = list(saved[cs_helpers.SCENARIO_INCLUDED])
            self._axes = [list(a) for a in saved[cs_helpers.SCENARIO_AXES]]
            self._mode = combine

            try:
                self.combined_dataframe()
            except Exception:
                self.clear_tables()
                cs_helpers.clear_scenario_persistence(name)
                QtWidgets.QMessageBox.warning(
                    self,
                    "Scenario reload failed",
                    "Saved scenario files could not be combined or were invalid. "
                    "Load scenario files from scratch.",
                )
                return

            if getattr(self, "_last_inclusion_mismatch", False):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Scenario selection reset",
                    "Scenario file columns no longer match the saved selection. "
                    "All valid scenarios were selected again.",
                )
        except Exception as e:
            self.clear_tables()
            cs_helpers.clear_scenario_persistence(name)
            QtWidgets.QMessageBox.warning(
                self,
                "Scenario reload failed",
                f"Could not reload saved scenario files.\n{e}\n\n"
                "Load scenario files from scratch.",
            )
        finally:
            progress.close()

    def _clear_combined_scenarios(self) -> None:
        self._scenario_dataframe = pd.DataFrame()
        self._included = []
        self._axes = []
        self._mode = None
        self.sync_combinations_panel()
        self.update_stats()
        self.refresh_save_button()

    def combined_dataframe(self, skip_checks: bool = False) -> None:
        """Updates scenario dataframe to contain the combined scenarios of multiple tables."""
        data = [df for df in (t.dataframe for t in self.tables) if not df.empty]
        if not data:
            self._clear_combined_scenarios()
            return

        kind = self.get_combine_type()
        manager = ss.SuperstructureManager(*data)
        self._scenario_dataframe = manager.combined_data(kind, skip_checks)
        self.reconcile_inclusion_after_combine()
        self.refresh_save_button()

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
        self.refresh_save_button()
        self.updateGeometry()

    def clear_tables(self) -> None:
        """Clear all scenario tables in certain cases (eg. project change)."""
        for w in self.tables:
            self.scenario_tables.removeWidget(w)
            w.deleteLater()
        self.tables = []
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

    def refresh_save_button(self) -> None:
        """Enable Save when a merged flow-scenario table is available."""
        self.save_scenario.setEnabled(not self._scenario_dataframe.empty)

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
        # Keep scenario columns in original order from imported files.
        scenarios = self._scenario_dataframe.columns.difference(
            ["input", "output", "flow"], sort=False
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
        """Compatibility hook after manual file load; state follows the combined table."""
        self.refresh_save_button()


class DatapackageScenarioPanel(QtWidgets.QWidget):
    """Path, scenario-name checkboxes, and selected-scenario count."""

    def __init__(self, section: ScenarioSection, parent=None):
        super().__init__(parent or section)
        self._section = section
        self._updating = False
        self._applied_path = ""

        self.path_edit = QtWidgets.QLineEdit(self)
        self.path_edit.setObjectName("scenario-datapackage-path")
        self.path_edit.setPlaceholderText("Scenario datapackage (.zip or directory)")
        self.browse_btn = QtWidgets.QPushButton("Browse...", self)
        self.browse_btn.setObjectName("scenario-datapackage-browse")

        path_row = QtWidgets.QHBoxLayout()
        path_row.setContentsMargins(10, 0, 0, 0)
        path_row.addWidget(widgets.ABLabel.demiBold("Datapackage:", self))
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(self.browse_btn)

        self.list = QtWidgets.QListWidget(self)
        self.list.setObjectName("scenario-datapackage-scenarios")
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)

        self.count_label = QtWidgets.QLabel(self)
        self.count_label.setObjectName("scenario-datapackage-count")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(path_row)
        layout.addWidget(self.list, stretch=1)
        layout.addWidget(self.count_label)
        self.setLayout(layout)
        self.update_count()

        self.browse_btn.clicked.connect(self._browse)
        self.path_edit.editingFinished.connect(self._path_edited)
        self.list.itemChanged.connect(self._on_item_changed)

    def path(self) -> str:
        return self.path_edit.text().strip()

    def included_names(self) -> list[str]:
        names = []
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                names.append(item.text())
        return names

    def show_scenarios(self, path: str, names: list[str], included: list[str]) -> None:
        included_set = set(included)
        self._updating = True
        self.path_edit.blockSignals(True)
        self.list.blockSignals(True)
        try:
            self.path_edit.setText(str(path))
            self._applied_path = str(path)
            self.list.clear()
            for name in names:
                item = QtWidgets.QListWidgetItem(name)
                item.setFlags(
                    item.flags()
                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                    | QtCore.Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(
                    QtCore.Qt.CheckState.Checked
                    if name in included_set
                    else QtCore.Qt.CheckState.Unchecked
                )
                self.list.addItem(item)
        finally:
            self.list.blockSignals(False)
            self.path_edit.blockSignals(False)
            self._updating = False
        self.update_count()

    def clear(self) -> None:
        self._updating = True
        self.path_edit.blockSignals(True)
        self.list.blockSignals(True)
        try:
            self.path_edit.clear()
            self.list.clear()
            self._applied_path = ""
        finally:
            self.list.blockSignals(False)
            self.path_edit.blockSignals(False)
            self._updating = False
        self.update_count()

    def update_count(self) -> None:
        total = self.list.count()
        selected = len(self.included_names())
        self.count_label.setText(
            f"Selected scenarios: <b>{selected}</b> / <b>{total}</b>"
        )

    def _browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption="Choose scenario datapackage",
            filter="Datapackage (*.zip);;All files (*)",
        )
        if path:
            self._section.use_datapackage_path(path)

    def _path_edited(self) -> None:
        if self._updating or self.path() == self._applied_path:
            return
        self._section.use_datapackage_path(self.path())

    def _on_item_changed(self, _item: QtWidgets.QListWidgetItem) -> None:
        if self._updating:
            return
        self._section.on_datapackage_inclusion_changed()


class ScenarioCombinationsPanel(QtWidgets.QWidget):
    """Checkbox list of product-combined scenario names."""

    def __init__(self, section: ScenarioSection, parent=None):
        super().__init__(parent or section)
        self._section = section
        self._updating = False

        title = widgets.ABLabel.demiBold("Scenarios to calculate", self)
        self.select_all_btn = QtWidgets.QPushButton("Select all", self)
        self.select_none_btn = QtWidgets.QPushButton("Select none", self)
        self.list = QtWidgets.QListWidget(self)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.select_all_btn)
        buttons.addWidget(self.select_none_btn)
        buttons.addStretch(1)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(title)
        layout.addLayout(buttons)
        layout.addWidget(self.list)
        self.setLayout(layout)

        self.select_all_btn.clicked.connect(self._section.select_all_combinations)
        self.select_none_btn.clicked.connect(self._section.select_none_combinations)
        self.list.itemChanged.connect(self._on_item_changed)

    def set_combinations(self, rows: list[tuple[str, bool]]) -> None:
        self._updating = True
        self.list.blockSignals(True)
        self.list.clear()
        for name, active in rows:
            item = QtWidgets.QListWidgetItem(name)
            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(
                QtCore.Qt.CheckState.Checked
                if active
                else QtCore.Qt.CheckState.Unchecked
            )
            self.list.addItem(item)
        self.list.blockSignals(False)
        self._updating = False

    def _on_item_changed(self, item: QtWidgets.QListWidgetItem) -> None:
        if self._updating:
            return
        active = item.checkState() == QtCore.Qt.CheckState.Checked
        self._section.set_combination_included(item.text(), active)


class ScenarioImportWidget(QtWidgets.QWidget):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.index = index
        self.file_path = None
        self.sheet_index = None
        self.csv_separator = ";"
        self.scenario_name = QtWidgets.QLabel("<filename>", self)
        self.load_btn = QtWidgets.QPushButton(icons.qicons.import_db, "Load")
        self.load_btn.setToolTip("Load (new) data for this scenario table")
        refresh_icon = self.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_BrowserReload
        )
        self.reload_btn = QtWidgets.QToolButton(self)
        self.reload_btn.setIcon(refresh_icon)
        self.reload_btn.setToolTip("Reload the same scenario file from disk")
        self.reload_btn.setEnabled(False)
        self.remove_btn = QtWidgets.QPushButton(icons.qicons.delete, "Delete")
        self.remove_btn.setToolTip("Remove this scenario table")
        self.view = ScenarioImportView(self)
        self.model = ScenarioImportModel(parent=self)
        self.view.setModel(self.model)
        self.scenario_df = pd.DataFrame(columns=ss.SUPERSTRUCTURE)

        layout = QtWidgets.QVBoxLayout()

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.scenario_name)
        row.addWidget(self.load_btn)
        row.addWidget(self.reload_btn)
        row.addStretch(1)
        row.addWidget(self.remove_btn)

        layout.addLayout(row)
        layout.addWidget(self.view)
        layout.addStretch(1)
        self.setLayout(layout)
        self.connect_signals()

    def connect_signals(self):
        self.load_btn.clicked.connect(self.load_action)
        self.reload_btn.clicked.connect(self.reload_action)
        parent = self.parent()
        if parent and isinstance(parent, ScenarioSection):
            self.remove_btn.clicked.connect(lambda: parent.remove_table(self.index))
            self.remove_btn.clicked.connect(parent.can_add_table)

    def _update_filename_label(self, path: Path | None, *, ok: bool) -> None:
        """Show the scenario file name; style red when the last load failed."""
        if path is None:
            self.scenario_name.setText("<filename>")
            self.scenario_name.setToolTip("")
            self.scenario_name.setStyleSheet("")
            return
        path = Path(path)
        self.scenario_name.setText(path.name)
        self.scenario_name.setToolTip(str(path))
        if ok:
            self.scenario_name.setStyleSheet("")
        else:
            self.scenario_name.setStyleSheet(
                "color: #c62828; font-weight: bold;"
            )

    def _warn_load_failed(self, path: Path, *, title: str = "Could not load scenario file") -> None:
        while QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.warning(
            self,
            title,
            f"Could not load scenario file:\n{path}\n\n"
            "No usable scenario data was found. If Excel has the file open, "
            "save it and try again, or close Excel so Activity Browser can "
            "read it. Otherwise check that the file is a valid flow- or "
            "parameter-scenario file.",
        )

    def load_action(self) -> None:
        dialog = ExcelReadDialog(self)
        if dialog.exec_() != ExcelReadDialog.DialogCode.Accepted:
            return

        path = dialog.path
        idx = dialog.import_sheet.currentIndex()
        separator = dialog.field_separator.currentData()
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok = self.load_from_path(
                path, sheet_index=idx, separator=separator or ";"
            )
            if ok:
                self._parent.save_button(True)
        finally:
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()

    def reload_action(self) -> None:
        if not self.file_path:
            return
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok = self.load_from_path(
                self.file_path,
                sheet_index=self.sheet_index,
                separator=self.csv_separator,
            )
            if ok:
                self._parent.save_button(True)
        finally:
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()

    @staticmethod
    def _looks_like_flow_sdf(df: pd.DataFrame) -> bool:
        return (
            df is not None
            and not df.empty
            and ss.is_flow_sdf_headers(df.columns)
        )

    @staticmethod
    def _looks_like_broken_flow_sdf(df: pd.DataFrame) -> bool:
        return (
            df is not None
            and not df.empty
            and ss.is_partial_flow_sdf_headers(df.columns)
        )

    @staticmethod
    def _looks_like_parameter_scenarios(df: pd.DataFrame) -> bool:
        return (
            df is not None
            and not df.empty
            and len(df.columns.intersection({"Name", "Group"})) == 2
        )

    def _warn_header_mismatch(self, path: Path, columns) -> None:
        missing = ss.missing_superstructure_columns(columns)
        while QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()
        missing_html = ", ".join(f'"{m}"' for m in missing)
        msg = (
            "<p>The scenario file header does not match the expected flow-scenario "
            f"columns.</p><p>Missing or misspelled required column(s):<br>{missing_html}"
            "</p><p>Expected headers:<br>"
            + ss.edit_superstructure_for_string(sep=", ", fhighlight='"')
            + "</p>"
            f"<p>File:<br>{path}</p>"
        )
        critical = ss.ABPopup.abCritical(
            "Invalid scenario file header", msg, QtWidgets.QPushButton("Cancel")
        )
        critical.exec_()

    def _read_excel_scenario_df(
        self, path: Path, sheet_index: int | None
    ) -> pd.DataFrame:
        """Read an Excel scenario sheet; probe sheets if index missing/invalid."""
        candidates: list[int] = []
        if sheet_index is not None:
            candidates.append(int(sheet_index))
        try:
            names = ss.get_sheet_names(path) or []
        except Exception:
            names = []
        for i in range(len(names)):
            if i not in candidates:
                candidates.append(i)
        if not candidates:
            candidates = [0, 1]

        for idx in candidates:
            df = ss.import_from_excel(path, idx)
            if (
                self._looks_like_flow_sdf(df)
                or self._looks_like_broken_flow_sdf(df)
                or self._looks_like_parameter_scenarios(df)
            ):
                self.sheet_index = idx
                return df
        return pd.DataFrame()

    def load_from_path(
        self,
        path: Path,
        *,
        sheet_index: int | None = 1,
        separator: str = ";",
        combine: bool = True,
        quiet: bool = False,
    ) -> bool:
        """Load a scenario file from disk. Returns False on user-cancel / bad type."""
        path = Path(path)
        file_type_suffix = path.suffix.lower()
        logger.info("Loading Scenario file. This may take a while for large files")
        self.file_path = path
        self.csv_separator = separator

        try:
            if file_type_suffix == ".feather":
                df = ss.ABFeatherImporter.read_file(path)
                self.sheet_index = None
            elif file_type_suffix.startswith(".xls"):
                df = self._read_excel_scenario_df(path, sheet_index)
            else:
                df = ss.ABCSVImporter.read_file(path, separator=separator)
                self.sheet_index = None
        except Exception:
            logger.exception("Failed to read scenario file: {}", path)
            df = pd.DataFrame()

        if df is None or getattr(df, "empty", False):
            logger.warning("Scenario file read returned no usable data: {}", path)
            self._update_filename_label(path, ok=False)
            self.reload_btn.setEnabled(
                self.file_path is not None and Path(self.file_path).is_file()
            )
            if not quiet:
                self._warn_load_failed(path)
            return False

        if self._looks_like_broken_flow_sdf(df):
            self._update_filename_label(path, ok=False)
            self.reload_btn.setEnabled(
                self.file_path is not None and Path(self.file_path).is_file()
            )
            if not quiet:
                self._warn_header_mismatch(path, df.columns)
            return False

        if self._looks_like_flow_sdf(df):
            self.sync_superstructure(df, combine=combine)
        elif self._looks_like_parameter_scenarios(df):
            logger.info(
                "Superstructure: Attempting to read as parameter scenario file."
            )
            if not pd.api.types.is_string_dtype(df["Group"]):
                df["Group"] = df["Group"].astype("str")
            self.sync_superstructure(ss.parameters_to_sdf(df), combine=combine)
        else:
            self._update_filename_label(path, ok=False)
            self.reload_btn.setEnabled(
                self.file_path is not None and Path(self.file_path).is_file()
            )
            if quiet:
                return False
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()
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
            critical.exec_()
            return False

        ok = not self.scenario_df.empty
        self._update_filename_label(path, ok=ok)
        self.reload_btn.setEnabled(True)
        return ok

    def sync_superstructure(self, df: pd.DataFrame, combine: bool = True) -> None:
        """synchronizes the contents of either a single, or multiple scenario files to create a single scenario
        dataframe"""
        # Drop any wait cursor so the DB-check dialog can use a normal pointer.
        QtWidgets.QApplication.restoreOverrideCursor()
        df = self.scenario_db_check(df)
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            df = ss.SuperstructureManager.fill_empty_process_keys_in_exchanges(df)
            ss.SuperstructureManager.verify_scenario_process_keys(df)
            df = ss.SuperstructureManager.check_duplicates(df)
            # If we've cancelled the import then we don't want to load the dataframe
            if df.empty:
                return
            self.scenario_df = df
            cols = ss.scenario_names_from_df(self.scenario_df)
            self._set_scenario_name_rows(cols, [True] * len(cols))
            if combine:
                self._parent.combined_dataframe()
        finally:
            # Nested code may restore/re-set for its own dialogs; clear any leftover wait.
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()

    def _set_scenario_name_rows(
        self, cols: list[str], flags: list[bool]
    ) -> None:
        self.model.set_dataframe(
            pd.DataFrame({"Scenarios": cols, "_active": list(flags)})
        )

    def sync_inclusion_flags(self, flags: list[bool]) -> None:
        if self.scenario_df.empty:
            return
        cols = ss.scenario_names_from_df(self.scenario_df)
        if len(flags) != len(cols):
            flags = [True] * len(cols)
        self._set_scenario_name_rows(cols, flags)

    def scenario_db_check(self, df: pd.DataFrame) -> pd.DataFrame:
        dbs = set(df.loc[:, "from database"]).union(set(df.loc[:, "to database"]))
        # Ignore missing / non-string cells (e.g. NaN) — they are not DB names.
        dbs = {db for db in dbs if isinstance(db, str) and db.strip()}
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
            logger.debug("No data in scenario table {}, skipping".format(self.index + 1))
        return self.scenario_df


class ScenarioImportView(widgets.ABTreeView):
    """Tree view for scenario imports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRootIsDecorated(False)

    def updateIndexColumnVisibility(self):
        self.setColumnHidden(0, False)
        self.setColumnWidth(0, 28)
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)

    def setDefaultColumnDelegates(self):
        super().setDefaultColumnDelegates()
        self.setItemDelegateForColumn(0, delegates.CheckboxDelegate(self))


class ScenarioImportModel(core.ABTreeModel):
    """Model for displaying imported scenario names with include checkboxes."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # QAbstractItemModel.parent(index) shadows QObject.parent(); keep an explicit ref.
        self.import_widget = parent if isinstance(parent, ScenarioImportWidget) else None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and self.indexUserCheckable(
            index
        ):
            on = bool(self.get(index, "_active"))
            return (
                QtCore.Qt.CheckState.Checked
                if on
                else QtCore.Qt.CheckState.Unchecked
            )
        if (
            role == QtCore.Qt.ItemDataRole.ForegroundRole
            and index.column() > 0
            and self.row(index) is not None
        ):
            if not bool(self.get(index, "_active")):
                return QtGui.QBrush(QtGui.QColor(QtCore.Qt.GlobalColor.gray))
        return super().data(index, role)

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and self.indexUserCheckable(
            index
        ):
            active = delegates.CheckboxDelegate.is_checked(value)
            name = self.get(index, "Scenarios")
            widget = self.import_widget
            section = widget._parent if widget is not None else None
            if section is not None and name is not None:
                data_tables = [t for t in section.tables if not t.dataframe.empty]
                try:
                    file_index = data_tables.index(widget)
                except ValueError:
                    return False
                section.set_name_included(file_index, str(name), active)
            return True
        return super().setData(index, value, role)

    def indexUserCheckable(self, index):
        return index.column() == 0 and self.row(index) is not None


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


class GetScenarioTemplateDialog(QtWidgets.QDialog):
    """Choose parameter vs flow starter template and csv/xlsx format."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Get scenario template")
        self.setWindowIcon(qicons.question)

        self.kind_group = QtWidgets.QButtonGroup(self)
        self.parameter_radio = QtWidgets.QRadioButton("Parameter scenarios", self)
        self.flow_radio = QtWidgets.QRadioButton("Flow scenarios", self)
        self.parameter_radio.setChecked(True)
        self.kind_group.addButton(self.parameter_radio)
        self.kind_group.addButton(self.flow_radio)

        kind_box = QtWidgets.QGroupBox("Template type", self)
        kind_layout = QtWidgets.QVBoxLayout(kind_box)
        kind_layout.addWidget(self.parameter_radio)
        kind_layout.addWidget(self.flow_radio)

        self.format_group = QtWidgets.QButtonGroup(self)
        self.xlsx_radio = QtWidgets.QRadioButton("Excel (.xlsx)", self)
        self.csv_radio = QtWidgets.QRadioButton("CSV (.csv)", self)
        self.xlsx_radio.setChecked(True)
        self.format_group.addButton(self.xlsx_radio)
        self.format_group.addButton(self.csv_radio)

        format_box = QtWidgets.QGroupBox("File format", self)
        format_layout = QtWidgets.QVBoxLayout(format_box)
        format_layout.addWidget(self.xlsx_radio)
        format_layout.addWidget(self.csv_radio)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(kind_box)
        layout.addWidget(format_box)
        layout.addWidget(buttons)

    def selection(self) -> tuple[str, str]:
        kind = "parameter" if self.parameter_radio.isChecked() else "flow"
        fmt = "xlsx" if self.xlsx_radio.isChecked() else "csv"
        return kind, fmt


class ScenariosHelpDialog(QtWidgets.QDialog):
    """Compact explanation of scenario modeling in the calculation setup."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scenario modeling")
        self.setWindowIcon(qicons.question)
        self.resize(520, 420)

        text = QtWidgets.QLabel(self)
        text.setWordWrap(True)
        text.setTextFormat(Qt.RichText)
        text.setText(
            "<h3>Scenario modeling in Activity Browser</h3>"
            "<p>In <b>Scenario</b> mode, alternative values for flows or parameters can "
            "can be defined. Each scenario can thus consider different flow or parameter values defined in two types of scenario files.</p>"
            "<h4>Flow scenarios</h4>"
            "<p>A <b>flow-scenario</b> file (scenario difference file) identifies flows (left-side part)"
            "(e.g. inputs from one to another activity) and contains scenario values for each flow (right-side part). "
            "In an empty file, you can start by adding rows via <b>Copy for scenario file</b> on processes or flows, then paste "
            "into a template from <b>Template...</b>.</p>"
            "<h4>Parameter scenarios</h4>"
            "<p>A <b>parameter-scenario</b> file varies Brightway parameters across scenarios."
            "The columns are Name and Group (mandatory to identify parameters), then optional default values (as in the database), plus scenario columns. "
            "When you load it, AB converts it into flow scenarios for calculation.</p>"
            "<h4>Several scenario files</h4>"
            "<p>Use <b>Add scenarios...</b> more than once. "
            "<b>Combine scenarios</b> builds the product of scenario names across files (parameter and flow scenarios can be mixed); "
            "<b>Extend scenarios</b> aligns files on shared scenario names.</p>"
            "<h4>Template...</h4>"
            "<p>Download an empty flow or parameter starter (.xlsx or .csv). "
            "If the project has parameters, the parameter template is filled with "
            "Name / Group / default and empty example scenario columns.</p>"
            "<h4>Save...</h4>"
            "<p>Writes the currently loaded, merged flow-scenario table to a file.</p>"
            "<h4>Notes</h4> "
            "<p>Lines starting with <b>#</b> and columns starting with <b>_</b> are ignored on import "
            "(useful for your notes).</p>"
        )
        text.setOpenExternalLinks(False)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(text)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, parent=self)
        buttons.accepted.connect(self.accept)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

