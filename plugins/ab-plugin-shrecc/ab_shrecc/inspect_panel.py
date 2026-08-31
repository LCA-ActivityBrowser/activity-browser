# -*- coding: utf-8 -*-
"""Inspect stage: Create results in collapsible sections."""
from __future__ import annotations

from qtpy import QtCore, QtWidgets

from .configure_section import ConfigureSection


class _TablePayloadModel(QtCore.QAbstractTableModel):
    def __init__(self, payload: dict | None = None, parent=None):
        super().__init__(parent)
        self._columns: list[str] = []
        self._rows: list[list] = []
        if payload:
            self.set_payload(payload)

    def set_payload(self, payload: dict | None) -> None:
        self.beginResetModel()
        if not payload:
            self._columns = []
            self._rows = []
        else:
            self._columns = list(payload.get("columns") or [])
            self._rows = list(payload.get("rows") or [])
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return None
        value = self._rows[index.row()][index.column()]
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal and section < len(self._columns):
            return self._columns[section]
        if orientation == QtCore.Qt.Vertical:
            return str(section + 1)
        return None


class InspectPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        self.mismatch_banner = QtWidgets.QLabel()
        self.mismatch_banner.setWordWrap(True)
        self.mismatch_banner.setStyleSheet("color: #d32f2f;")
        self.mismatch_banner.hide()
        layout.addWidget(self.mismatch_banner)

        self.ready_label = QtWidgets.QLabel()
        self.ready_label.hide()
        layout.addWidget(self.ready_label)

        self.year_combo = QtWidgets.QComboBox()
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        layout.addWidget(self.year_combo)

        self._sections: dict[str, ConfigureSection] = {}

        summary_content = QtWidgets.QWidget()
        summary_layout = QtWidgets.QVBoxLayout(summary_content)
        self.summary_table = QtWidgets.QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(
            ["Year", "Source", "Background DB", "Output DB"]
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        summary_layout.addWidget(self.summary_table)
        self._add_section(layout, "summary", "Resolved config", summary_content)

        gaps_content = QtWidgets.QWidget()
        gaps_layout = QtWidgets.QVBoxLayout(gaps_content)
        self.gap_banner = QtWidgets.QLabel()
        self.gap_banner.setWordWrap(True)
        gaps_layout.addWidget(self.gap_banner)
        self.mapping_table = QtWidgets.QTableView()
        self.mapping_model = _TablePayloadModel()
        self.mapping_table.setModel(self.mapping_model)
        gaps_layout.addWidget(self.mapping_table)
        self._add_section(layout, "mapping", "Mapping gaps", gaps_content)

        preview_content = QtWidgets.QWidget()
        preview_layout = QtWidgets.QVBoxLayout(preview_content)
        self.column_sum_label = QtWidgets.QLabel()
        self.column_sum_label.setWordWrap(True)
        preview_layout.addWidget(self.column_sum_label)
        self.preview_table = QtWidgets.QTableView()
        self.preview_model = _TablePayloadModel()
        self.preview_table.setModel(self.preview_model)
        preview_layout.addWidget(self.preview_table)
        self._add_section(layout, "preview", "Inventory preview", preview_content)

        log_content = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_content)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        log_layout.addWidget(self.log_view)
        self._add_section(layout, "log", "Create log", log_content)

        layout.addStretch()

        self._artifacts: dict = {}
        self._enabled = False
        self.set_enabled(False)

    def _add_section(
        self,
        layout: QtWidgets.QVBoxLayout,
        section_id: str,
        title: str,
        content: QtWidgets.QWidget,
    ) -> None:
        section = ConfigureSection(title, content, expanded=False)
        self._sections[section_id] = section
        layout.addWidget(section)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        for widget in (
            self.summary_table,
            self.gap_banner,
            self.mapping_table,
            self.column_sum_label,
            self.preview_table,
            self.log_view,
            self.year_combo,
        ):
            widget.setEnabled(enabled)
        for section in self._sections.values():
            section.setEnabled(enabled)

    def show_configuration_mismatch(self, message: str | None = None) -> None:
        self.mismatch_banner.setText(
            message
            or (
                "Configuration changed after Create. Create again before Write. "
                "The results below are from the last Create."
            )
        )
        self.mismatch_banner.show()
        self.ready_label.hide()
        # Keep last artifacts visible for review.
        if self._artifacts:
            self.set_enabled(True)

    def show_ready(self) -> None:
        self.ready_label.setText("Ready to write.")
        self.ready_label.show()
        self.mismatch_banner.hide()

    def hide_banners(self) -> None:
        self.mismatch_banner.hide()
        self.ready_label.hide()

    def show_stale(self, message: str) -> None:
        """Backward-compatible alias for configuration mismatch."""
        self.show_configuration_mismatch(message)

    def set_artifacts(self, artifacts: dict | None) -> None:
        new_artifacts = artifacts or {}
        changed = new_artifacts != self._artifacts
        self._artifacts = new_artifacts
        if not self._artifacts:
            self.set_enabled(False)
            self._clear_tables()
            return
        self.set_enabled(True)
        self._populate_summary()
        self._populate_year_selector()
        self._populate_log()
        if changed:
            self._collapse_all_sections()

    def _collapse_all_sections(self) -> None:
        for section in self._sections.values():
            section.set_expanded(False)

    def _clear_tables(self) -> None:
        self.summary_table.setRowCount(0)
        self.mapping_model.set_payload(None)
        self.preview_model.set_payload(None)
        self.gap_banner.setText("No mapping gap report.")
        self.column_sum_label.setText("")
        self.log_view.clear()
        self.year_combo.clear()

    def _populate_summary(self) -> None:
        rows = self._artifacts.get("summary") or []
        self.summary_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                str(row.get("year", "")),
                str(row.get("source", "")),
                str(row.get("background_db", "")),
                str(row.get("output_db", "")),
            ]
            for column_index, value in enumerate(values):
                self.summary_table.setItem(
                    row_index,
                    column_index,
                    QtWidgets.QTableWidgetItem(value),
                )
        section = self._sections.get("summary")
        if section is not None:
            section.set_summary(f"{len(rows)} year(s)" if rows else "No rows")

    def _populate_year_selector(self) -> None:
        years = self._artifacts.get("years") or []
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for year in years:
            self.year_combo.addItem(str(year), year)
        self.year_combo.blockSignals(False)
        if years:
            self._on_year_changed()

    def _populate_log(self) -> None:
        lines = list(self._artifacts.get("log") or [])
        warnings = self._artifacts.get("warnings") or []
        if warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in warnings)
        self.log_view.setPlainText("\n".join(lines))
        section = self._sections.get("log")
        if section is not None:
            section.set_summary(f"{len(lines)} line(s)" if lines else "Empty")

    def _on_year_changed(self) -> None:
        year = self.year_combo.currentData()
        if year is None:
            return
        mapping = (self._artifacts.get("mapping_reports") or {}).get(year)
        mapping_section = self._sections.get("mapping")
        if mapping:
            self.gap_banner.setText(
                "Mapping gaps detected for this year. Write is still allowed; "
                "strict mode may fail if background activities are missing."
            )
            self.mapping_model.set_payload(mapping)
            if mapping_section is not None:
                rows = mapping.get("rows") or []
                mapping_section.set_summary(f"{len(rows)} gap row(s)")
                mapping_section.set_status("Gaps", level="warn")
        else:
            self.gap_banner.setText("No mapping gap report for this year.")
            self.mapping_model.set_payload(None)
            if mapping_section is not None:
                mapping_section.set_summary("None")
                mapping_section.set_status("OK", level="ok")

        preview = (self._artifacts.get("table_previews") or {}).get(year)
        self.preview_model.set_payload(preview)
        sums = (self._artifacts.get("column_sums") or {}).get(year) or {}
        preview_section = self._sections.get("preview")
        if sums:
            parts = []
            for country, total in sorted(sums.items()):
                status = "ok" if abs(total - 1.0) <= 0.01 else "check"
                parts.append(f"{country}: {total:.4f} ({status})")
            self.column_sum_label.setText("Column sums: " + "; ".join(parts))
            if preview_section is not None:
                preview_section.set_summary(f"{len(sums)} country sum(s)")
        else:
            self.column_sum_label.setText("No inventory preview for this year.")
            if preview_section is not None:
                preview_section.set_summary("None")
