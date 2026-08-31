# -*- coding: utf-8 -*-
"""Inspect panels A–D on the Create & inspect stage."""
from __future__ import annotations

from qtpy import QtCore, QtWidgets


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
        self.stale_banner = QtWidgets.QLabel()
        self.stale_banner.setWordWrap(True)
        self.stale_banner.hide()
        layout.addWidget(self.stale_banner)

        self.ready_label = QtWidgets.QLabel()
        self.ready_label.hide()
        layout.addWidget(self.ready_label)

        self.year_combo = QtWidgets.QComboBox()
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        layout.addWidget(self.year_combo)

        summary_group = QtWidgets.QGroupBox("A. Resolved config summary")
        summary_layout = QtWidgets.QVBoxLayout(summary_group)
        self.summary_table = QtWidgets.QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(
            ["Year", "Source", "Background DB", "Output DB"]
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        summary_layout.addWidget(self.summary_table)
        layout.addWidget(summary_group)

        gaps_group = QtWidgets.QGroupBox("B. Mapping gaps")
        gaps_layout = QtWidgets.QVBoxLayout(gaps_group)
        self.gap_banner = QtWidgets.QLabel()
        self.gap_banner.setWordWrap(True)
        gaps_layout.addWidget(self.gap_banner)
        self.mapping_table = QtWidgets.QTableView()
        self.mapping_model = _TablePayloadModel()
        self.mapping_table.setModel(self.mapping_model)
        gaps_layout.addWidget(self.mapping_table)
        layout.addWidget(gaps_group)

        preview_group = QtWidgets.QGroupBox("C. Inventory preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        self.column_sum_label = QtWidgets.QLabel()
        self.column_sum_label.setWordWrap(True)
        preview_layout.addWidget(self.column_sum_label)
        self.preview_table = QtWidgets.QTableView()
        self.preview_model = _TablePayloadModel()
        self.preview_table.setModel(self.preview_model)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_group)

        log_group = QtWidgets.QGroupBox("D. Create log")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group)

        self._artifacts: dict = {}
        self._enabled = False
        self.set_enabled(False)

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

    def show_stale(self, message: str) -> None:
        self.stale_banner.setText(message)
        self.stale_banner.show()
        self.ready_label.hide()
        self.set_enabled(False)
        self._clear_tables()

    def show_ready(self) -> None:
        self.ready_label.setText("Ready to write.")
        self.ready_label.show()

    def hide_banners(self) -> None:
        self.stale_banner.hide()
        self.ready_label.hide()

    def set_artifacts(self, artifacts: dict | None) -> None:
        self._artifacts = artifacts or {}
        self.hide_banners()
        if not self._artifacts:
            self.set_enabled(False)
            self._clear_tables()
            return
        self.set_enabled(True)
        self._populate_summary()
        self._populate_year_selector()
        self._populate_log()

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

    def _on_year_changed(self) -> None:
        year = self.year_combo.currentData()
        if year is None:
            return
        mapping = (self._artifacts.get("mapping_reports") or {}).get(year)
        if mapping:
            self.gap_banner.setText(
                "Mapping gaps detected for this year. Write is still allowed; "
                "strict mode may fail if background activities are missing."
            )
            self.mapping_model.set_payload(mapping)
        else:
            self.gap_banner.setText("No mapping gap report for this year.")
            self.mapping_model.set_payload(None)

        preview = (self._artifacts.get("table_previews") or {}).get(year)
        self.preview_model.set_payload(preview)
        sums = (self._artifacts.get("column_sums") or {}).get(year) or {}
        if sums:
            parts = []
            for country, total in sorted(sums.items()):
                status = "ok" if abs(total - 1.0) <= 0.01 else "check"
                parts.append(f"{country}: {total:.4f} ({status})")
            self.column_sum_label.setText("Column sums: " + "; ".join(parts))
        else:
            self.column_sum_label.setText("No inventory preview for this year.")
