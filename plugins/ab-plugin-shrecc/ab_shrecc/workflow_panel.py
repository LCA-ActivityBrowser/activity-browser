# -*- coding: utf-8 -*-
"""Single SHRECC workflow: stage tabs."""
from __future__ import annotations

from typing import Callable, Optional

from qtpy import QtWidgets

from . import ids
from .configure_form import ConfigureForm
from .configure_model import config_completion_errors
from .controller import ShreccPluginController, WorkflowState
from .inspect_panel import InspectPanel
from .write_panel import WritePanel


class WorkflowPanel(QtWidgets.QWidget):
    def __init__(
        self,
        workflow: WorkflowState,
        controller: ShreccPluginController,
        *,
        signals=None,
        start_create: Optional[Callable[[str], None]] = None,
        start_write: Optional[Callable[[str], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.workflow = workflow
        self.controller = controller
        self._host_signals = signals
        self._start_create = start_create
        self._start_write = start_write

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
        self.create_btn.clicked.connect(self._on_create_clicked)
        inspect_layout.addWidget(self.create_btn)
        self.inspect_panel = InspectPanel()
        inspect_layout.addWidget(self.inspect_panel, 1)
        self.stage_tabs.addTab(
            inspect_widget,
            ids.STAGE_LABELS[ids.STAGE_CREATE_INSPECT],
        )

        self.write_panel = WritePanel(
            workflow,
            controller,
            start_write=start_write,
            existing_databases=_database_names,
        )
        self._write_index = self.stage_tabs.addTab(
            self.write_panel,
            ids.STAGE_LABELS[ids.STAGE_WRITE],
        )
        self.stage_tabs.setTabEnabled(self._write_index, False)

        if self._host_signals is not None:
            self._host_signals.project.changed.connect(self.refresh)
            self._host_signals.meta.databases_changed.connect(self._refresh_databases)
            self._host_signals.database.written.connect(self._refresh_databases)
            self._host_signals.database.deleted.connect(self._refresh_databases)

        self.refresh()
        self.configure_form.config_changed.connect(self._on_config_changed)

    def _on_config_changed(self, config: dict) -> None:
        self.controller.update_config(self.workflow, config)
        self._refresh_ui()

    def _on_create_clicked(self) -> None:
        if self._start_create is None:
            return
        self._start_create(self.workflow.id)

    def _refresh_databases(self, *args) -> None:
        self.configure_form.set_database_names(_database_names())
        self._refresh_ui()

    def refresh(self) -> None:
        workflow = self.workflow
        stale = self.controller.is_project_stale(workflow)
        suffix = " ⚠ project stale" if stale else ""
        self.project_label.setText(f"Project: {workflow.project_name}{suffix}")
        self.configure_form.set_database_names(_database_names())
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        self._refresh_create_gating()
        self._refresh_inspect()
        self._refresh_write_tab()

    def _refresh_create_gating(self) -> None:
        workflow = self.workflow
        errors = config_completion_errors(self.controller.get_config(workflow))
        stale = self.controller.is_project_stale(workflow)
        can_create = self.controller.can_start_create(workflow)

        if workflow.create_status == "running":
            status = "Create running…"
        elif stale:
            status = "Create blocked: bound project differs from current project."
        elif errors:
            status = "Configure incomplete: " + " ".join(errors)
        elif self.controller.global_job is not None:
            status = "Create blocked while another plugin job is running."
        elif workflow.create_status == "done":
            status = "Create complete. Review inspect panels below."
        elif workflow.create_status == "stale":
            status = "Inspect stale: re-create after Configure changes."
        elif workflow.create_status == "failed":
            status = f"Create failed: {workflow.create_error}"
        else:
            status = "Configure complete. Ready to create."

        self.create_status_label.setText(status)
        self.configure_form.set_status_text(
            "" if not errors else " ".join(errors)
        )
        self.create_btn.setEnabled(can_create)

    def _refresh_inspect(self) -> None:
        workflow = self.workflow
        if workflow.create_status == "stale":
            self.inspect_panel.show_stale(
                "Configure changed after create. Re-create required before write."
            )
        elif workflow.create_status == "done":
            self.inspect_panel.set_artifacts(workflow.inspect_artifacts)
            self.inspect_panel.show_ready()
        elif workflow.create_status == "failed":
            self.inspect_panel.hide_banners()
            self.inspect_panel.set_artifacts(None)
        elif workflow.create_status == "running":
            self.inspect_panel.hide_banners()
            self.inspect_panel.set_artifacts(None)
        else:
            self.inspect_panel.hide_banners()
            self.inspect_panel.set_artifacts(None)

    def _refresh_write_tab(self) -> None:
        can_open = (
            self.workflow.create_status == "done"
            and self.workflow.create_handle is not None
        )
        self.stage_tabs.setTabEnabled(self._write_index, can_open)
        self.write_panel.refresh()


def _database_names() -> list[str]:
    import bw2data as bd

    return sorted(bd.databases)
