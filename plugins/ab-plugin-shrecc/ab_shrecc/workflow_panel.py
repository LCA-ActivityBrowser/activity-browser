# -*- coding: utf-8 -*-
"""Single SHRECC workflow: stage tabs."""
from __future__ import annotations

from qtpy import QtWidgets

from . import ids
from .configure_form import ConfigureForm
from .configure_model import config_completion_errors
from .controller import ShreccPluginController, WorkflowState


class WorkflowPanel(QtWidgets.QWidget):
    def __init__(
        self,
        workflow: WorkflowState,
        controller: ShreccPluginController,
        *,
        signals=None,
        parent=None,
    ):
        super().__init__(parent)
        self.workflow = workflow
        self.controller = controller
        self._host_signals = signals

        layout = QtWidgets.QVBoxLayout(self)
        self.project_label = QtWidgets.QLabel()
        layout.addWidget(self.project_label)

        self.stage_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.stage_tabs, 1)

        self.configure_form = ConfigureForm()
        self.configure_form.set_config(controller.get_config(workflow))
        self.stage_tabs.addTab(
            self.configure_form,
            ids.STAGE_LABELS[ids.STAGE_CONFIGURE],
        )

        inspect_widget = QtWidgets.QWidget()
        inspect_layout = QtWidgets.QVBoxLayout(inspect_widget)
        self.create_status_label = QtWidgets.QLabel(
            "Create is available when Configure is complete and the bound project "
            "matches the current Brightway project."
        )
        self.create_status_label.setWordWrap(True)
        inspect_layout.addWidget(self.create_status_label)
        self.create_btn = QtWidgets.QPushButton("Create")
        inspect_layout.addWidget(self.create_btn)
        inspect_layout.addWidget(
            QtWidgets.QLabel("Inspect results will be implemented in ticket 15.")
        )
        inspect_layout.addStretch()
        self.stage_tabs.addTab(
            inspect_widget,
            ids.STAGE_LABELS[ids.STAGE_CREATE_INSPECT],
        )

        self.stage_tabs.addTab(
            self._placeholder_stage("Write Brightway databases (ticket 16)."),
            ids.STAGE_LABELS[ids.STAGE_WRITE],
        )

        if self._host_signals is not None:
            self._host_signals.project.changed.connect(self.refresh)
            self._host_signals.meta.databases_changed.connect(self._refresh_databases)
            self._host_signals.database.written.connect(self._refresh_databases)
            self._host_signals.database.deleted.connect(self._refresh_databases)

        self.refresh()
        self.configure_form.config_changed.connect(self._on_config_changed)

    def _placeholder_stage(self, message: str) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        inner = QtWidgets.QVBoxLayout(widget)
        inner.addWidget(QtWidgets.QLabel(message))
        inner.addStretch()
        return widget

    def _on_config_changed(self, config: dict) -> None:
        self.controller.update_config(self.workflow, config)
        self._refresh_create_gating()

    def _refresh_databases(self, *args) -> None:
        self.configure_form.set_database_names(_database_names())
        self._refresh_create_gating()

    def refresh(self) -> None:
        workflow = self.workflow
        stale = self.controller.is_project_stale(workflow)
        suffix = " ⚠ project stale" if stale else ""
        self.project_label.setText(f"Project: {workflow.project_name}{suffix}")
        self.configure_form.set_database_names(_database_names())
        self._refresh_create_gating()

    def _refresh_create_gating(self) -> None:
        workflow = self.workflow
        errors = config_completion_errors(self.controller.get_config(workflow))
        stale = self.controller.is_project_stale(workflow)
        can_create = self.controller.can_start_create(workflow)

        if stale:
            status = "Create blocked: bound project differs from current project."
        elif errors:
            status = "Configure incomplete: " + " ".join(errors)
        elif self.controller.global_job is not None:
            status = "Create blocked while another plugin job is running."
        else:
            status = "Configure complete. Create will run in ticket 15."

        self.create_status_label.setText(status)
        self.configure_form.set_status_text(
            "" if not errors else " ".join(errors)
        )
        self.create_btn.setEnabled(can_create)


def _database_names() -> list[str]:
    import bw2data as bd

    return sorted(bd.databases)
