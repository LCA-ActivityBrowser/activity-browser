# -*- coding: utf-8 -*-
"""Write stage: Write options and write-plan table."""
from __future__ import annotations

from typing import Callable, Optional

from qtpy import QtWidgets

from .controller import ShreccPluginController, WorkflowState
from .run_button import style_run_button
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
        self._loading = False

        layout = QtWidgets.QVBoxLayout(self)
        self.project_label = QtWidgets.QLabel()
        self.project_label.setWordWrap(True)
        layout.addWidget(self.project_label)

        options_row = QtWidgets.QHBoxLayout()
        options_row.addWidget(QtWidgets.QLabel("Output database base name"))
        self.output_name_edit = QtWidgets.QLineEdit()
        self.output_name_edit.setText(workflow.output_db_base_name)
        self.output_name_edit.textChanged.connect(self._on_output_name_changed)
        options_row.addWidget(self.output_name_edit, 1)
        layout.addLayout(options_row)

        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)

        plan_group = QtWidgets.QGroupBox("Write plan")
        plan_layout = QtWidgets.QVBoxLayout(plan_group)
        self.summary_table = QtWidgets.QTableWidget(0, 5)
        self.summary_table.setHorizontalHeaderLabels(
            ["Year", "Source", "Background DB", "Output DB", "Status"]
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        plan_layout.addWidget(self.summary_table)
        layout.addWidget(plan_group)

        self.overwrite_confirm = QtWidgets.QCheckBox(
            "I confirm overwriting the existing databases listed above."
        )
        self.overwrite_confirm.hide()
        self.overwrite_confirm.toggled.connect(self._refresh_write_button)
        layout.addWidget(self.overwrite_confirm)

        self.hint_label = QtWidgets.QLabel(
            "After a successful write, open the Databases pane to browse the new inventories."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.hide()
        layout.addWidget(self.hint_label)

        layout.addStretch(1)

        write_row = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel(
            "Write is available after a successful Create when the workflow "
            "project matches the currently open project."
        )
        self.status_label.setWordWrap(True)
        write_row.addWidget(self.status_label, 1)
        self.write_progress = QtWidgets.QProgressBar()
        self.write_progress.setRange(0, 0)
        self.write_progress.setTextVisible(False)
        self.write_progress.setFixedWidth(120)
        self.write_progress.hide()
        write_row.addWidget(self.write_progress)
        self.write_btn = QtWidgets.QPushButton("Write")
        style_run_button(self.write_btn)
        self.write_btn.clicked.connect(self._on_write_clicked)
        write_row.addWidget(self.write_btn)
        layout.addLayout(write_row)

        self._targets: list[WriteTarget] = []
        self.refresh()

    def _on_write_clicked(self) -> None:
        if self._start_write is None:
            return
        self._start_write(self.workflow.id)

    def _on_output_name_changed(self, text: str) -> None:
        if self._loading:
            return
        self.controller.update_output_db_base_name(self.workflow, text)
        self._refresh_plan()
        self._refresh_status()
        self._refresh_write_button()

    def refresh(self) -> None:
        workflow = self.workflow
        project_mismatch = self.controller.is_project_mismatch(workflow)
        project_text = f"Workflow project: {workflow.project_name}"
        if project_mismatch:
            project_text += (
                f" — does not match the open project "
                f"(“{self.controller.current_project_name()}”)"
            )
        self.project_label.setText(project_text)

        self._loading = True
        if self.output_name_edit.text() != workflow.output_db_base_name:
            self.output_name_edit.setText(workflow.output_db_base_name)
        self._loading = False

        self._refresh_plan()
        self._refresh_status()
        self._refresh_write_button()

    def _refresh_plan(self) -> None:
        workflow = self.workflow
        names = self.controller.resolved_output_database_names(workflow)
        if names:
            self.preview_label.setText(
                "Per-year names: "
                + "; ".join(f"{year}→{name}" for year, name in sorted(names.items()))
            )
        else:
            self.preview_label.setText("Per-year names: (no years yet)")

        self._targets = []
        if workflow.create_handle is not None:
            self._targets = write_targets(
                workflow.create_handle,
                self._existing_databases(),
                output_names=names,
                summary_rows=(workflow.inspect_artifacts or {}).get("summary") or [],
            )
        self._populate_summary()

        overwrite_needed = needs_overwrite_confirm(self._targets)
        self.overwrite_confirm.setVisible(overwrite_needed)
        if not overwrite_needed:
            self.overwrite_confirm.setChecked(False)

    def _populate_summary(self) -> None:
        self.summary_table.setRowCount(len(self._targets))
        for row_index, target in enumerate(self._targets):
            status = "Will overwrite" if target.will_overwrite else "New"
            values = (
                str(target.year),
                target.source,
                target.background_db,
                target.database_name,
                status,
            )
            for column_index, value in enumerate(values):
                self.summary_table.setItem(
                    row_index,
                    column_index,
                    QtWidgets.QTableWidgetItem(value),
                )

    def _refresh_status(self) -> None:
        workflow = self.workflow
        running = workflow.write_status == "running"
        self.write_progress.setVisible(running)

        if not str(workflow.output_db_base_name or "").strip():
            self.status_label.setText("Enter an output database base name.")
            self.hint_label.hide()
            return

        if workflow.create_status == "config_mismatch":
            self.status_label.setText(
                "Configuration changed after Create. Create again before Write."
            )
            self.hint_label.hide()
            return

        if running:
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
                "Complete Create and review Inspect before writing."
            )
        self.hint_label.hide()

    def _refresh_write_button(self) -> None:
        workflow = self.workflow
        can_write = self.controller.can_start_write(workflow)
        if can_write and needs_overwrite_confirm(self._targets):
            can_write = self.overwrite_confirm.isChecked()
        self.write_btn.setEnabled(can_write and bool(self._targets))
        self.write_btn.setText(self.controller.write_action_label(workflow))
