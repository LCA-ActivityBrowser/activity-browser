# -*- coding: utf-8 -*-
"""Write stage summary and controls."""
from __future__ import annotations

from typing import Callable, Optional

from qtpy import QtWidgets

from .controller import ShreccPluginController, WorkflowState
from .write_service import WriteTarget, needs_overwrite_confirm, write_targets


class WritePanel(QtWidgets.QWidget):
    def __init__(
        self,
        workflow: WorkflowState,
        controller: ShreccPluginController,
        *,
        start_write: Optional[Callable[[str], None]] = None,
        existing_databases: Callable[[], list[str]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.workflow = workflow
        self.controller = controller
        self._start_write = start_write
        self._existing_databases = existing_databases or (lambda: [])

        layout = QtWidgets.QVBoxLayout(self)
        self.project_label = QtWidgets.QLabel()
        self.project_label.setWordWrap(True)
        layout.addWidget(self.project_label)

        summary_group = QtWidgets.QGroupBox("Output databases")
        summary_layout = QtWidgets.QVBoxLayout(summary_group)
        self.summary_table = QtWidgets.QTableWidget(0, 3)
        self.summary_table.setHorizontalHeaderLabels(
            ["Year", "Database", "Status"]
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        summary_layout.addWidget(self.summary_table)
        layout.addWidget(summary_group)

        self.overwrite_confirm = QtWidgets.QCheckBox(
            "I confirm overwriting the existing databases listed above."
        )
        self.overwrite_confirm.hide()
        self.overwrite_confirm.toggled.connect(self._refresh_write_button)
        layout.addWidget(self.overwrite_confirm)

        self.write_btn = QtWidgets.QPushButton("Write to Brightway")
        self.write_btn.clicked.connect(self._on_write_clicked)
        layout.addWidget(self.write_btn)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.hint_label = QtWidgets.QLabel(
            "After a successful write, open the Databases pane to browse the new inventories."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

        layout.addStretch()
        self._targets: list[WriteTarget] = []
        self.refresh()

    def _on_write_clicked(self) -> None:
        if self._start_write is None:
            return
        self._start_write(self.workflow.id)

    def refresh(self) -> None:
        workflow = self.workflow
        stale = self.controller.is_project_stale(workflow)
        project_text = f"Brightway project: {workflow.project_name}"
        if stale:
            project_text += " (stale — switch back or start a new workflow)"
        self.project_label.setText(project_text)

        self._targets = []
        if workflow.create_handle is not None:
            self._targets = write_targets(
                workflow.create_handle,
                self._existing_databases(),
            )
        self._populate_summary()

        overwrite_needed = needs_overwrite_confirm(self._targets)
        self.overwrite_confirm.setVisible(overwrite_needed)
        if not overwrite_needed:
            self.overwrite_confirm.setChecked(False)

        self._refresh_status()
        self._refresh_write_button()

    def _populate_summary(self) -> None:
        self.summary_table.setRowCount(len(self._targets))
        for row_index, target in enumerate(self._targets):
            status = "Will overwrite" if target.will_overwrite else "New"
            for column_index, value in enumerate(
                (str(target.year), target.database_name, status)
            ):
                self.summary_table.setItem(
                    row_index,
                    column_index,
                    QtWidgets.QTableWidgetItem(value),
                )

    def _refresh_status(self) -> None:
        workflow = self.workflow
        if workflow.create_status == "stale":
            self.status_label.setText(
                "Inspect is stale. Re-create on the Configure / Create tab before writing."
            )
            self.hint_label.hide()
            return

        if workflow.write_status == "running":
            self.status_label.setText("Writing databases…")
            self.hint_label.hide()
            return

        if workflow.write_status == "done" and workflow.written_database_names:
            names = ", ".join(
                f"{year}→{name}"
                for year, name in sorted(workflow.written_database_names.items())
            )
            self.status_label.setText(
                f"Written to Brightway project {workflow.project_name}: {names}"
            )
            self.hint_label.show()
            return

        if workflow.write_status == "failed":
            message = workflow.write_error or "Write failed."
            if workflow.partial_written_names:
                partial = ", ".join(
                    f"{year}→{name}"
                    for year, name in sorted(workflow.partial_written_names.items())
                )
                message += f" Partial writes refreshed: {partial}."
            self.status_label.setText(message)
            self.hint_label.hide()
            return

        if self.controller.can_start_write(workflow):
            self.status_label.setText("Ready to write.")
        else:
            self.status_label.setText(
                "Complete create and inspect before writing."
            )
        self.hint_label.hide()

    def _refresh_write_button(self) -> None:
        workflow = self.workflow
        can_write = self.controller.can_start_write(workflow)
        if can_write and needs_overwrite_confirm(self._targets):
            can_write = self.overwrite_confirm.isChecked()
        self.write_btn.setEnabled(can_write and bool(self._targets))
