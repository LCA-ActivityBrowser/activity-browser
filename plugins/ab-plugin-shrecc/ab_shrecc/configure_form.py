# -*- coding: utf-8 -*-
"""Configure stage form for SHRECC NewDatabase kwargs."""
from __future__ import annotations

from qtpy import QtCore, QtWidgets

from .configure_model import (
    configure_section_summaries,
    default_config,
    normalize_config,
    preview_database_names,
    resolved_sources,
)
from .configure_section import ConfigureSection
from .run_button import style_run_button
from .shrecc_choices import (
    consumption_profiles,
    energy_charts_countries,
    iam_choices,
    inventory_resolutions,
    needs_tyndp_fields,
    tyndp_climate_years,
    tyndp_scenarios,
    valid_sources,
    zero_consumption_modes,
)


class ConfigureForm(QtWidgets.QWidget):
    """Editable SHRECC configuration; emits ``config_changed`` on edits."""

    config_changed = QtCore.Signal(dict)
    switch_project_requested = QtCore.Signal()
    create_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._database_names: list[str] = []
        self._loading = False
        self._sections: dict[str, ConfigureSection] = {}

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setSpacing(8)

        project_content = QtWidgets.QWidget()
        project_layout = QtWidgets.QVBoxLayout(project_content)
        self.project_value = QtWidgets.QLabel()
        self.project_value.setWordWrap(True)
        self.project_mismatch = QtWidgets.QLabel()
        self.project_mismatch.setWordWrap(True)
        self.project_mismatch.setStyleSheet("color: #d32f2f;")
        self.project_mismatch.hide()
        self.switch_project_btn = QtWidgets.QPushButton("Switch to current project")
        self.switch_project_btn.hide()
        self.switch_project_btn.clicked.connect(self.switch_project_requested.emit)
        self.project_hint = QtWidgets.QLabel(
            "This workflow uses a Brightway project for Create and Write. "
            "Those actions only run when it matches the project currently open "
            "in Activity Browser."
        )
        self.project_hint.setWordWrap(True)
        self.project_hint.setStyleSheet("color: #616161;")
        project_layout.addWidget(self.project_value)
        project_layout.addWidget(self.project_mismatch)
        project_layout.addWidget(self.switch_project_btn)
        project_layout.addWidget(self.project_hint)
        self._add_section(layout, "project", "Project", project_content)
        self._project_name = ""
        self._project_stale = False
        self._current_project_name = ""

        years_content = QtWidgets.QWidget()
        years_layout = QtWidgets.QHBoxLayout(years_content)
        self.years_list = QtWidgets.QListWidget()
        self.years_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        years_layout.addWidget(self.years_list, 1)
        year_buttons = QtWidgets.QVBoxLayout()
        self.add_year_spin = QtWidgets.QSpinBox()
        self.add_year_spin.setRange(1990, 2100)
        self.add_year_spin.setValue(2025)
        self.add_year_btn = QtWidgets.QPushButton("Add year")
        self.remove_year_btn = QtWidgets.QPushButton("Remove selected")
        year_buttons.addWidget(self.add_year_spin)
        year_buttons.addWidget(self.add_year_btn)
        year_buttons.addWidget(self.remove_year_btn)
        year_buttons.addStretch()
        years_layout.addLayout(year_buttons)
        self._add_section(layout, "years", "Years", years_content)

        countries_content = QtWidgets.QWidget()
        countries_layout = QtWidgets.QHBoxLayout(countries_content)
        self.available_countries = QtWidgets.QListWidget()
        self.available_countries.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.selected_countries = QtWidgets.QListWidget()
        self.selected_countries.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        country_buttons = QtWidgets.QVBoxLayout()
        self.add_country_btn = QtWidgets.QPushButton("→")
        self.remove_country_btn = QtWidgets.QPushButton("←")
        country_buttons.addWidget(self.add_country_btn)
        country_buttons.addWidget(self.remove_country_btn)
        country_buttons.addStretch()
        countries_layout.addWidget(QtWidgets.QLabel("Available"))
        countries_layout.addWidget(self.available_countries, 1)
        countries_layout.addLayout(country_buttons)
        countries_layout.addWidget(QtWidgets.QLabel("Selected"))
        countries_layout.addWidget(self.selected_countries, 1)
        self._add_section(layout, "countries", "Countries", countries_content)

        time_content = QtWidgets.QWidget()
        time_layout = QtWidgets.QVBoxLayout(time_content)
        self.time_mode_group = QtWidgets.QButtonGroup(self)
        self.time_range_radio = QtWidgets.QRadioButton("Time range")
        self.hour_range_radio = QtWidgets.QRadioButton("Hour range within time range")
        self.times_radio = QtWidgets.QRadioButton("Explicit timestamps")
        for radio in (self.time_range_radio, self.hour_range_radio, self.times_radio):
            self.time_mode_group.addButton(radio)
            time_layout.addWidget(radio)
        self.time_range_radio.setChecked(True)

        range_row = QtWidgets.QHBoxLayout()
        self.time_start_edit = QtWidgets.QLineEdit()
        self.time_end_edit = QtWidgets.QLineEdit()
        range_row.addWidget(QtWidgets.QLabel("Start"))
        range_row.addWidget(self.time_start_edit, 1)
        range_row.addWidget(QtWidgets.QLabel("End"))
        range_row.addWidget(self.time_end_edit, 1)
        time_layout.addLayout(range_row)

        hour_row = QtWidgets.QHBoxLayout()
        self.hour_start_spin = QtWidgets.QSpinBox()
        self.hour_start_spin.setRange(0, 23)
        self.hour_end_spin = QtWidgets.QSpinBox()
        self.hour_end_spin.setRange(0, 23)
        self.hour_end_spin.setValue(23)
        hour_row.addWidget(QtWidgets.QLabel("Hour start"))
        hour_row.addWidget(self.hour_start_spin)
        hour_row.addWidget(QtWidgets.QLabel("Hour end"))
        hour_row.addWidget(self.hour_end_spin)
        hour_row.addStretch()
        time_layout.addLayout(hour_row)

        self.times_edit = QtWidgets.QPlainTextEdit()
        self.times_edit.setPlaceholderText(
            "One timestamp per line, e.g. 2025-06-01 00:00:00"
        )
        self.times_edit.setMaximumHeight(80)
        time_layout.addWidget(self.times_edit)
        self._add_section(layout, "time", "Time selection", time_content)

        source_content = QtWidgets.QWidget()
        source_layout = QtWidgets.QFormLayout(source_content)
        self.source_combo = QtWidgets.QComboBox()
        for source in valid_sources():
            self.source_combo.addItem(source, source)
        source_layout.addRow("Source", self.source_combo)
        self._add_section(layout, "source", "Source", source_content)

        tyndp_content = QtWidgets.QWidget()
        tyndp_layout = QtWidgets.QFormLayout(tyndp_content)
        self.tyndp_scenario_combo = QtWidgets.QComboBox()
        self.tyndp_scenario_combo.addItem("— select —", None)
        for scenario in tyndp_scenarios():
            self.tyndp_scenario_combo.addItem(scenario, scenario)
        self.climate_year_combo = QtWidgets.QComboBox()
        self.climate_year_combo.addItem("— select —", None)
        for year in tyndp_climate_years():
            self.climate_year_combo.addItem(str(year), year)
        self.iam_combo = QtWidgets.QComboBox()
        for iam in iam_choices():
            self.iam_combo.addItem(iam, iam)
        tyndp_layout.addRow("TYNDP scenario", self.tyndp_scenario_combo)
        tyndp_layout.addRow("Climate year", self.climate_year_combo)
        tyndp_layout.addRow("IAM", self.iam_combo)
        self._add_section(layout, "tyndp", "TYNDP", tyndp_content)

        db_content = QtWidgets.QWidget()
        db_layout = QtWidgets.QVBoxLayout(db_content)
        self.map_bg_by_year_check = QtWidgets.QCheckBox(
            "Map background database per year"
        )
        db_layout.addWidget(self.map_bg_by_year_check)
        single_row = QtWidgets.QHBoxLayout()
        self.bg_db_combo = QtWidgets.QComboBox()
        self.bg_db_combo.setEditable(True)
        single_row.addWidget(QtWidgets.QLabel("Background database"))
        single_row.addWidget(self.bg_db_combo, 1)
        db_layout.addLayout(single_row)
        self.bg_db_table = QtWidgets.QTableWidget(0, 2)
        self.bg_db_table.setHorizontalHeaderLabels(["Year", "Background database"])
        self.bg_db_table.horizontalHeader().setStretchLastSection(True)
        db_layout.addWidget(self.bg_db_table)
        output_row = QtWidgets.QHBoxLayout()
        self.my_db_name_edit = QtWidgets.QLineEdit()
        output_row.addWidget(QtWidgets.QLabel("Output database base name"))
        output_row.addWidget(self.my_db_name_edit, 1)
        db_layout.addLayout(output_row)
        self.output_preview = QtWidgets.QLabel()
        self.output_preview.setWordWrap(True)
        db_layout.addWidget(self.output_preview)
        self.resolution_combo = QtWidgets.QComboBox()
        for resolution in inventory_resolutions():
            self.resolution_combo.addItem(resolution, resolution)
        resolution_row = QtWidgets.QHBoxLayout()
        resolution_row.addWidget(QtWidgets.QLabel("Inventory resolution"))
        resolution_row.addWidget(self.resolution_combo, 1)
        db_layout.addLayout(resolution_row)
        self._add_section(
            layout,
            "databases",
            "Background database(s)",
            db_content,
        )

        advanced_content = QtWidgets.QWidget()
        advanced_layout = QtWidgets.QFormLayout(advanced_content)
        self.strict_check = QtWidgets.QCheckBox("Strict activity matching at write")
        self.strict_check.setChecked(True)
        self.cutoff_spin = QtWidgets.QDoubleSpinBox()
        self.cutoff_spin.setDecimals(6)
        self.cutoff_spin.setRange(0.0, 1.0)
        self.cutoff_spin.setSingleStep(0.0001)
        self.cutoff_spin.setValue(1e-3)
        self.include_cutoff_check = QtWidgets.QCheckBox("Include cutoff residual")
        self.include_cutoff_check.setChecked(True)
        self.network_check = QtWidgets.QCheckBox("Include network exchanges")
        self.network_check.setChecked(True)
        self.zero_consumption_combo = QtWidgets.QComboBox()
        for mode in zero_consumption_modes():
            self.zero_consumption_combo.addItem(mode, mode)
        self.consumption_profile_combo = QtWidgets.QComboBox()
        for profile in consumption_profiles():
            self.consumption_profile_combo.addItem(profile, profile)
        self.download_check = QtWidgets.QCheckBox("Allow source download")
        self.download_check.setChecked(True)
        self.verbose_check = QtWidgets.QCheckBox("Verbose logging")
        self.check_check = QtWidgets.QCheckBox("Run conservation checks")
        self.check_check.setChecked(True)
        self.include_mix_check = QtWidgets.QCheckBox(
            "Include consumption mix volume in results"
        )
        self.include_mix_check.setChecked(True)
        self.retain_hourly_check = QtWidgets.QCheckBox("Retain hourly results")
        self.retain_hourly_check.setChecked(True)
        advanced_layout.addRow(self.strict_check)
        advanced_layout.addRow("Cutoff", self.cutoff_spin)
        advanced_layout.addRow(self.include_cutoff_check)
        advanced_layout.addRow(self.network_check)
        advanced_layout.addRow("Zero consumption", self.zero_consumption_combo)
        advanced_layout.addRow("Consumption profile", self.consumption_profile_combo)
        advanced_layout.addRow(self.download_check)
        advanced_layout.addRow(self.verbose_check)
        advanced_layout.addRow(self.check_check)
        advanced_layout.addRow(self.include_mix_check)
        advanced_layout.addRow(self.retain_hourly_check)
        self._add_section(layout, "advanced", "Advanced", advanced_content)

        layout.addStretch()

        scroll.setWidget(body)
        root = QtWidgets.QVBoxLayout(self)
        root.addWidget(scroll, 1)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        create_row = QtWidgets.QHBoxLayout()
        self.create_status_label = QtWidgets.QLabel(
            "Create is available when Configure is complete and the workflow "
            "project matches the currently open project."
        )
        self.create_status_label.setWordWrap(True)
        create_row.addWidget(self.create_status_label, 1)
        self.create_progress = QtWidgets.QProgressBar()
        self.create_progress.setRange(0, 0)
        self.create_progress.setTextVisible(False)
        self.create_progress.setFixedWidth(120)
        self.create_progress.hide()
        create_row.addWidget(self.create_progress)
        self.create_btn = QtWidgets.QPushButton("Create")
        style_run_button(self.create_btn)
        self.create_btn.clicked.connect(self.create_requested.emit)
        create_row.addWidget(self.create_btn)
        root.addLayout(create_row)

        self._populate_country_lists(set())
        self._wire_signals()
        self.set_config(default_config())

    def _add_section(
        self,
        layout: QtWidgets.QVBoxLayout,
        section_id: str,
        title: str,
        content: QtWidgets.QWidget,
        *,
        expanded: bool = False,
    ) -> None:
        section = ConfigureSection(title, content, expanded=expanded)
        self._sections[section_id] = section
        layout.addWidget(section)

    def set_project(
        self,
        project_name: str,
        *,
        stale: bool = False,
        current_project_name: str | None = None,
    ) -> None:
        self._project_name = project_name
        self._project_stale = stale
        self._current_project_name = current_project_name or ""
        self.project_value.setText(f"Workflow project: {project_name or '(none)'}")
        section = self._sections.get("project")
        if section is None:
            return
        if stale:
            current = self._current_project_name or "(unknown)"
            self.project_mismatch.setText(
                f"This workflow uses project “{project_name}”. "
                f"The currently open project is “{current}”. Switch?"
            )
            self.project_mismatch.show()
            self.switch_project_btn.show()
            section.set_summary(f"{project_name} ≠ {current}")
            section.set_status("Mismatch", level="error")
            section.set_expanded(True)
        else:
            self.project_mismatch.hide()
            self.switch_project_btn.hide()
            section.set_summary(project_name)
            section.set_status("OK", level="ok")

    def set_database_names(self, names: list[str]) -> None:
        self._loading = True
        self._database_names = sorted(names)
        self._refresh_database_combos()
        self._loading = False
        self._update_section_summaries()

    def set_config(self, config: dict) -> None:
        self._loading = True
        config = normalize_config(config)

        self.years_list.clear()
        for year in config["years"]:
            self.years_list.addItem(str(year))

        selected = set(config["countries"])
        self._populate_country_lists(selected)

        time_mode = config.get("time_mode", "range")
        if time_mode == "hour_range":
            self.hour_range_radio.setChecked(True)
        elif time_mode == "times":
            self.times_radio.setChecked(True)
        else:
            self.time_range_radio.setChecked(True)
        self.time_start_edit.setText(config.get("time_range_start", ""))
        self.time_end_edit.setText(config.get("time_range_end", ""))
        self.hour_start_spin.setValue(int(config.get("hour_range_start", 0)))
        self.hour_end_spin.setValue(int(config.get("hour_range_end", 23)))
        self.times_edit.setPlainText(config.get("times_text", ""))

        self._set_combo_data(self.source_combo, config.get("source", "auto"))
        if config.get("tyndp_scenario"):
            self._set_combo_data(self.tyndp_scenario_combo, config["tyndp_scenario"])
        else:
            self._set_combo_data(self.tyndp_scenario_combo, None)
        if config.get("climate_year") is not None:
            self._set_combo_data(self.climate_year_combo, int(config["climate_year"]))
        else:
            self._set_combo_data(self.climate_year_combo, None)
        self._set_combo_data(self.iam_combo, config.get("iam", "remind-eu"))

        self.map_bg_by_year_check.setChecked(bool(config.get("map_bg_db_by_year")))
        self._set_combo_text(self.bg_db_combo, config.get("bg_db_name", ""))
        self._rebuild_bg_db_table(config)
        self.my_db_name_edit.setText(config.get("my_db_name", ""))
        self._set_combo_data(
            self.resolution_combo,
            config.get("inventory_resolution", "annual"),
        )

        self.strict_check.setChecked(bool(config.get("strict", True)))
        self.cutoff_spin.setValue(float(config.get("cutoff", 1e-3)))
        self.include_cutoff_check.setChecked(bool(config.get("include_cutoff", True)))
        self.network_check.setChecked(bool(config.get("network", True)))
        self._set_combo_data(
            self.zero_consumption_combo,
            config.get("zero_consumption", zero_consumption_modes()[0]),
        )
        self._set_combo_data(
            self.consumption_profile_combo,
            config.get("consumption_profile", consumption_profiles()[0]),
        )
        self.download_check.setChecked(bool(config.get("download", True)))
        self.verbose_check.setChecked(bool(config.get("verbose", False)))
        self.check_check.setChecked(bool(config.get("check", True)))
        self.include_mix_check.setChecked(
            bool(config.get("include_consumption_mix_volume", True))
        )
        self.retain_hourly_check.setChecked(
            bool(config.get("retain_hourly_results", True))
        )

        self._update_time_mode_visibility()
        self._update_tyndp_visibility()
        self._update_bg_db_visibility()
        self._update_output_preview()
        self._update_section_summaries()
        self._loading = False

    def current_config(self) -> dict:
        years = sorted(
            int(self.years_list.item(i).text())
            for i in range(self.years_list.count())
        )
        countries = [
            self.selected_countries.item(i).text()
            for i in range(self.selected_countries.count())
        ]
        if self.hour_range_radio.isChecked():
            time_mode = "hour_range"
        elif self.times_radio.isChecked():
            time_mode = "times"
        else:
            time_mode = "range"

        bg_db_by_year = {}
        for row in range(self.bg_db_table.rowCount()):
            year_item = self.bg_db_table.item(row, 0)
            combo = self.bg_db_table.cellWidget(row, 1)
            if year_item is None or combo is None:
                continue
            bg_db_by_year[year_item.text()] = combo.currentText()

        config = {
            "years": years,
            "countries": countries,
            "time_mode": time_mode,
            "time_range_start": self.time_start_edit.text().strip(),
            "time_range_end": self.time_end_edit.text().strip(),
            "hour_range_start": self.hour_start_spin.value(),
            "hour_range_end": self.hour_end_spin.value(),
            "times_text": self.times_edit.toPlainText(),
            "source": self.source_combo.currentData(),
            "tyndp_scenario": self.tyndp_scenario_combo.currentData(),
            "climate_year": self.climate_year_combo.currentData(),
            "iam": self.iam_combo.currentData(),
            "map_bg_db_by_year": self.map_bg_by_year_check.isChecked(),
            "bg_db_name": self.bg_db_combo.currentText().strip(),
            "bg_db_by_year": bg_db_by_year,
            "my_db_name": self.my_db_name_edit.text().strip(),
            "inventory_resolution": self.resolution_combo.currentData(),
            "strict": self.strict_check.isChecked(),
            "cutoff": self.cutoff_spin.value(),
            "include_cutoff": self.include_cutoff_check.isChecked(),
            "network": self.network_check.isChecked(),
            "zero_consumption": self.zero_consumption_combo.currentData(),
            "consumption_profile": self.consumption_profile_combo.currentData(),
            "download": self.download_check.isChecked(),
            "verbose": self.verbose_check.isChecked(),
            "check": self.check_check.isChecked(),
            "include_consumption_mix_volume": self.include_mix_check.isChecked(),
            "retain_hourly_results": self.retain_hourly_check.isChecked(),
        }
        return normalize_config(config)

    def set_status_text(self, text: str) -> None:
        self.status_label.setText(text)
        if text:
            self.status_label.setStyleSheet("color: #d32f2f;")
        else:
            self.status_label.setStyleSheet("")

    def set_create_status(self, text: str, *, running: bool = False) -> None:
        self.create_status_label.setText(text)
        self.create_progress.setVisible(running)

    def set_create_enabled(self, enabled: bool) -> None:
        self.create_btn.setEnabled(enabled)

    def set_create_label(self, text: str) -> None:
        self.create_btn.setText(text)

    def _wire_signals(self) -> None:
        self.add_year_btn.clicked.connect(self._on_add_year)
        self.remove_year_btn.clicked.connect(self._on_remove_years)
        self.add_country_btn.clicked.connect(self._on_add_countries)
        self.remove_country_btn.clicked.connect(self._on_remove_countries)
        self.time_mode_group.buttonClicked.connect(self._on_time_mode_changed)
        self.map_bg_by_year_check.toggled.connect(self._on_bg_map_toggled)

        widgets = [
            self.years_list,
            self.selected_countries,
            self.time_start_edit,
            self.time_end_edit,
            self.hour_start_spin,
            self.hour_end_spin,
            self.times_edit,
            self.source_combo,
            self.tyndp_scenario_combo,
            self.climate_year_combo,
            self.iam_combo,
            self.bg_db_combo,
            self.my_db_name_edit,
            self.resolution_combo,
            self.strict_check,
            self.cutoff_spin,
            self.include_cutoff_check,
            self.network_check,
            self.zero_consumption_combo,
            self.consumption_profile_combo,
            self.download_check,
            self.verbose_check,
            self.check_check,
            self.include_mix_check,
            self.retain_hourly_check,
        ]
        for widget in widgets:
            if isinstance(widget, QtWidgets.QComboBox):
                widget.currentIndexChanged.connect(self._emit_config_changed)
            elif isinstance(widget, QtWidgets.QAbstractSpinBox):
                widget.valueChanged.connect(self._emit_config_changed)
            elif isinstance(widget, QtWidgets.QPlainTextEdit):
                widget.textChanged.connect(self._emit_config_changed)
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.textChanged.connect(self._emit_config_changed)
            elif isinstance(widget, QtWidgets.QAbstractButton):
                widget.toggled.connect(self._emit_config_changed)

    def _populate_country_lists(self, selected: set[str]) -> None:
        self.available_countries.clear()
        self.selected_countries.clear()
        for country in energy_charts_countries():
            if country in selected:
                self.selected_countries.addItem(country)
            else:
                self.available_countries.addItem(country)

    def _on_add_year(self) -> None:
        year = self.add_year_spin.value()
        existing = {
            int(self.years_list.item(i).text())
            for i in range(self.years_list.count())
        }
        if year in existing:
            return
        self.years_list.addItem(str(year))
        self.years_list.sortItems()
        self._rebuild_bg_db_table(self.current_config())
        self._emit_config_changed()

    def _on_remove_years(self) -> None:
        for item in self.years_list.selectedItems():
            self.years_list.takeItem(self.years_list.row(item))
        self._rebuild_bg_db_table(self.current_config())
        self._emit_config_changed()

    def _on_add_countries(self) -> None:
        for item in self.available_countries.selectedItems():
            self.selected_countries.addItem(item.text())
            self.available_countries.takeItem(self.available_countries.row(item))
        self.selected_countries.sortItems()
        self._emit_config_changed()

    def _on_remove_countries(self) -> None:
        for item in self.selected_countries.selectedItems():
            self.available_countries.addItem(item.text())
            self.selected_countries.takeItem(self.selected_countries.row(item))
        self.available_countries.sortItems()
        self._emit_config_changed()

    def _on_time_mode_changed(self) -> None:
        self._update_time_mode_visibility()
        self._emit_config_changed()

    def _on_bg_map_toggled(self, checked: bool) -> None:
        self._update_bg_db_visibility()
        if checked:
            self._rebuild_bg_db_table(self.current_config())
        self._emit_config_changed()

    def _update_time_mode_visibility(self) -> None:
        hour_mode = self.hour_range_radio.isChecked()
        times_mode = self.times_radio.isChecked()
        self.hour_start_spin.setEnabled(hour_mode)
        self.hour_end_spin.setEnabled(hour_mode)
        self.times_edit.setEnabled(times_mode)
        range_enabled = not times_mode
        self.time_start_edit.setEnabled(range_enabled)
        self.time_end_edit.setEnabled(range_enabled)

    def _update_tyndp_visibility(self) -> None:
        visible = needs_tyndp_fields(self.current_config())
        self._sections["tyndp"].setVisible(visible)

    def _update_bg_db_visibility(self) -> None:
        by_year = self.map_bg_by_year_check.isChecked()
        self.bg_db_combo.setVisible(not by_year)
        self.bg_db_table.setVisible(by_year)

    def _update_output_preview(self) -> None:
        config = self.current_config()
        names = preview_database_names(config)
        if not names:
            self.output_preview.setText("Output preview: (configure years and name)")
            return
        sources = resolved_sources(config)
        lines = [
            f"{year}: {name} ({sources.get(year, '?')})"
            for year, name in sorted(names.items())
        ]
        self.output_preview.setText("Output preview: " + "; ".join(lines))

    def _update_section_summaries(self) -> None:
        summaries = configure_section_summaries(self.current_config())
        for section_id, section in self._sections.items():
            info = summaries.get(section_id)
            if info is None:
                continue
            section.set_summary(info.summary)
            section.set_status(info.status, level=info.level)

    def _rebuild_bg_db_table(self, config: dict) -> None:
        years = config.get("years") or []
        by_year = config.get("bg_db_by_year") or {}
        self.bg_db_table.setRowCount(len(years))
        for row, year in enumerate(years):
            year_item = QtWidgets.QTableWidgetItem(str(year))
            year_item.setFlags(year_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.bg_db_table.setItem(row, 0, year_item)
            combo = QtWidgets.QComboBox()
            combo.setEditable(True)
            combo.addItems(self._database_names)
            value = by_year.get(str(year)) or by_year.get(year) or ""
            self._set_combo_text(combo, value)
            combo.currentTextChanged.connect(self._emit_config_changed)
            self.bg_db_table.setCellWidget(row, 1, combo)

    def _refresh_database_combos(self) -> None:
        current_bg = self.bg_db_combo.currentText()
        self.bg_db_combo.clear()
        self.bg_db_combo.addItems(self._database_names)
        self._set_combo_text(self.bg_db_combo, current_bg)
        for row in range(self.bg_db_table.rowCount()):
            combo = self.bg_db_table.cellWidget(row, 1)
            if combo is None:
                continue
            value = combo.currentText()
            combo.clear()
            combo.addItems(self._database_names)
            self._set_combo_text(combo, value)

    def _emit_config_changed(self, *args) -> None:
        if self._loading:
            return
        self._update_tyndp_visibility()
        self._update_output_preview()
        self._update_section_summaries()
        self.config_changed.emit(self.current_config())

    @staticmethod
    def _set_combo_data(combo: QtWidgets.QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _set_combo_text(combo: QtWidgets.QComboBox, text: str) -> None:
        combo.setCurrentText(text or "")
