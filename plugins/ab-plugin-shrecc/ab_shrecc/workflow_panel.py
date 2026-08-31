# -*- coding: utf-8 -*-
"""Single SHRECC workflow: Configure / Inspect / Write stages."""
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
        switch_project: Optional[Callable[[str], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.workflow = workflow
        self.controller = controller
        self._host_signals = signals
        self._start_create = start_create
        self._start_write = start_write
        self._switch_project = switch_project

        layout = QtWidgets.QVBoxLayout(self)

        self.stage_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.stage_tabs, 1)

        self.configure_form = ConfigureForm()
        self.configure_form.set_config(controller.get_config(workflow))
        self.configure_form.switch_project_requested.connect(self._on_switch_project)
        self.configure_form.create_requested.connect(self._on_create_clicked)
        self._configure_index = self.stage_tabs.addTab(
            self.configure_form,
            ids.STAGE_LABELS[ids.STAGE_CONFIGURE],
        )

        self.inspect_panel = InspectPanel()
        self._inspect_index = self.stage_tabs.addTab(
            self.inspect_panel,
            ids.STAGE_LABELS[ids.STAGE_INSPECT],
        )
        self.stage_tabs.setTabEnabled(self._inspect_index, False)

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

        # Compat for tests that still look for create_btn on the panel.
        self.create_btn = self.configure_form.create_btn
        self.create_progress = self.configure_form.create_progress
        self.create_status_label = self.configure_form.create_status_label

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

    def _on_switch_project(self) -> None:
        if self._switch_project is None:
            return
        self._switch_project(self.workflow.id)

    def _refresh_databases(self, *args) -> None:
        self.configure_form.set_database_names(_database_names())
        self._refresh_ui()

    def refresh(self) -> None:
        workflow = self.workflow
        stale = self.controller.is_project_stale(workflow)
        self.configure_form.set_project(
            workflow.project_name,
            stale=stale,
            current_project_name=self.controller.current_project_name(),
        )
        self.configure_form.set_database_names(_database_names())
        self._refresh_ui()

    def select_inspect_stage(self) -> None:
        if self.controller.is_inspect_stage_available(self.workflow):
            self.stage_tabs.setCurrentIndex(self._inspect_index)

    def _refresh_ui(self) -> None:
        self._refresh_create_gating()
        self._refresh_inspect()
        self._refresh_stage_tabs()
        self.write_panel.refresh()

    def _refresh_create_gating(self) -> None:
        workflow = self.workflow
        errors = config_completion_errors(self.controller.get_config(workflow))
        stale = self.controller.is_project_stale(workflow)
        can_create = self.controller.can_start_create(workflow)
        running = workflow.create_status == "running"

        if running:
            status = "Create running…"
        elif stale:
            current = self.controller.current_project_name()
            status = (
                f"Create blocked: this workflow uses project "
                f"“{workflow.project_name}”; the open project is “{current}”."
            )
        elif errors:
            status = "Configure incomplete: " + " ".join(errors)
        elif self.controller.global_job is not None:
            status = "Create blocked while another plugin job is running."
        elif workflow.create_status == "done":
            status = "Create complete. Review Inspect."
        elif workflow.create_status == "stale":
            status = (
                "Configuration changed after Create. Create again before Write."
            )
        elif workflow.create_status == "failed":
            status = f"Create failed: {workflow.create_error}"
        else:
            status = "Configure complete. Ready to create."

        self.configure_form.set_create_status(status, running=running)
        self.configure_form.set_status_text(
            "" if not errors else " ".join(errors)
        )
        self.configure_form.set_create_enabled(can_create)
        self.configure_form.set_create_label(
            self.controller.create_action_label(workflow)
        )

    def _refresh_inspect(self) -> None:
        workflow = self.workflow
        if workflow.create_status == "stale":
            self.inspect_panel.set_artifacts(workflow.inspect_artifacts)
            self.inspect_panel.show_configuration_mismatch()
        elif workflow.create_status == "done":
            self.inspect_panel.set_artifacts(workflow.inspect_artifacts)
            self.inspect_panel.show_ready()
        elif workflow.create_status == "failed":
            if workflow.inspect_artifacts:
                self.inspect_panel.set_artifacts(workflow.inspect_artifacts)
                self.inspect_panel.show_configuration_mismatch(
                    f"Create failed: {workflow.create_error or 'unknown error'}. "
                    "Previous Inspect results are still shown. Create again before Write."
                )
            else:
                self.inspect_panel.hide_banners()
                self.inspect_panel.set_artifacts(None)
        elif workflow.create_status == "running":
            if workflow.inspect_artifacts:
                self.inspect_panel.set_artifacts(workflow.inspect_artifacts)
                self.inspect_panel.hide_banners()
            else:
                self.inspect_panel.hide_banners()
                self.inspect_panel.set_artifacts(None)
        else:
            self.inspect_panel.hide_banners()
            self.inspect_panel.set_artifacts(None)

    def _refresh_stage_tabs(self) -> None:
        self.stage_tabs.setTabEnabled(
            self._inspect_index,
            self.controller.is_inspect_stage_available(self.workflow),
        )
        self.stage_tabs.setTabEnabled(
            self._write_index,
            self.controller.is_write_stage_available(self.workflow),
        )


def _database_names() -> list[str]:
    import bw2data as bd

    return sorted(bd.databases)
