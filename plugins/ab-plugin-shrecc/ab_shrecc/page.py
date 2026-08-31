# -*- coding: utf-8 -*-
"""SHRECC plugin main page."""
from __future__ import annotations

from qtpy import QtWidgets

from activity_browser.plugins import ABAbstractPage

from .controller import ShreccPluginController, WorkflowState
from .create_worker import CreateWorker
from .write_service import refresh_written_databases, run_write
from .host_adapter import ShreccPluginHost
from .workflow_panel import WorkflowPanel


class ShreccPluginPage(ABAbstractPage):
    title = "SHRECC"
    basePage = True

    def __init__(
        self,
        *args,
        signals=None,
        host: ShreccPluginHost | None = None,
        plugin_settings=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._host_signals = signals
        self._host = host
        self._plugin_settings = plugin_settings
        self.controller = ShreccPluginController()
        self._panels: dict[str, WorkflowPanel] = {}
        self._create_workers: dict[str, CreateWorker] = {}

        root = QtWidgets.QVBoxLayout(self)

        toolbar = QtWidgets.QHBoxLayout()
        self.new_btn = QtWidgets.QPushButton("New workflow")
        self.duplicate_btn = QtWidgets.QPushButton("Duplicate workflow")
        self.close_btn = QtWidgets.QPushButton("Close workflow")
        toolbar.addWidget(self.new_btn)
        toolbar.addWidget(self.duplicate_btn)
        toolbar.addWidget(self.close_btn)
        toolbar.addStretch()
        self.job_banner = QtWidgets.QLabel()
        toolbar.addWidget(self.job_banner)
        root.addLayout(toolbar)

        self.workflow_tabs = QtWidgets.QTabWidget()
        self.workflow_tabs.setTabsClosable(True)
        self.workflow_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.workflow_tabs.currentChanged.connect(self._on_current_tab_changed)
        root.addWidget(self.workflow_tabs, 1)

        self.new_btn.clicked.connect(self._on_new_workflow)
        self.duplicate_btn.clicked.connect(self._on_duplicate_workflow)
        self.close_btn.clicked.connect(self._on_close_current_workflow)

        if self._host_signals is not None:
            self._host_signals.project.changed.connect(self._on_project_changed)

        self._refresh_job_banner()

    def showEvent(self, event):
        # Bind workflows when the page is actually shown, using the live project.
        self.controller.sync_pristine_workflows_to_current()
        self._ensure_workflow_tab()
        self._refresh_all_panels()
        super().showEvent(event)

    def _plugin_data_dir(self) -> str | None:
        data = self._plugin_settings
        if data is None:
            return None
        text = str(data.get("data_dir", "") or "").strip()
        return text or None

    def _ensure_workflow_tab(self) -> None:
        if not self.controller.workflows:
            self._add_workflow_tab(self.controller.new_workflow())

    def _add_workflow_tab(self, workflow: WorkflowState) -> None:
        panel = WorkflowPanel(
            workflow,
            self.controller,
            signals=self._host_signals,
            start_create=self._start_create,
            start_write=self._start_write,
            switch_project=self._switch_workflow_project,
        )
        self._panels[workflow.id] = panel
        index = self.workflow_tabs.addTab(panel, workflow.label)
        self.workflow_tabs.setCurrentIndex(index)

    def _start_create(self, workflow_id: str) -> None:
        if self._host is None:
            return
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None or not self.controller.can_start_create(workflow):
            return

        kwargs = self.controller.build_new_database_kwargs(
            workflow,
            data_dir=self._plugin_data_dir(),
        )
        self.controller.begin_create(workflow)
        self._refresh_all_panels()

        worker = CreateWorker(kwargs, self._host, parent=self)
        self._create_workers[workflow_id] = worker
        worker.completed.connect(
            lambda ndb, artifacts, wid=workflow_id: self._on_create_completed(
                wid, ndb, artifacts
            )
        )
        worker.failed.connect(
            lambda message, wid=workflow_id: self._on_create_failed(wid, message)
        )
        worker.finished.connect(
            lambda wid=workflow_id: self._create_workers.pop(wid, None)
        )
        worker.start()

    def _start_write(self, workflow_id: str) -> None:
        if self._host is None:
            return
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None or not self.controller.can_start_write(workflow):
            return
        create_handle = workflow.create_handle
        if create_handle is None:
            return

        self.controller.begin_write(workflow)
        self._refresh_all_panels()

        host = self._host

        result = host.run_blocking_operation(
            "Writing SHRECC databases",
            lambda: run_write(create_handle),
            cancellable=False,
        )
        # Refresh metadata only after the write thread releases SQLite.
        refresh_written_databases(result.written, host.after_database_write)

        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None or workflow.write_status != "running":
            return
        if result.succeeded:
            self.controller.complete_write(workflow, result.written)
        else:
            self.controller.fail_write(
                workflow,
                result.error or "Write failed.",
                result.written,
            )
        self._refresh_all_panels()

    def _on_create_completed(
        self,
        workflow_id: str,
        create_handle,
        artifacts: dict,
    ) -> None:
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None or workflow.create_status != "running":
            return
        self.controller.complete_create(workflow, create_handle, artifacts)
        self._refresh_all_panels()
        panel = self._panels.get(workflow_id)
        if panel is not None:
            panel.select_inspect_stage()

    def _on_create_failed(self, workflow_id: str, message: str) -> None:
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None or workflow.create_status != "running":
            return
        self.controller.fail_create(workflow, message)
        self._refresh_all_panels()

    def _switch_workflow_project(self, workflow_id: str) -> None:
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None:
            return
        if not self.controller.is_project_stale(workflow):
            return
        if workflow.create_status == "running" or workflow.write_status == "running":
            QtWidgets.QMessageBox.information(
                self,
                "Job running",
                "Wait for the current create/write job to finish before switching projects.",
            )
            return
        if (
            workflow.create_succeeded_unwritten
            or workflow.create_handle is not None
            or workflow.inspect_artifacts
        ):
            answer = QtWidgets.QMessageBox.question(
                self,
                "Switch project?",
                (
                    f"Switch this workflow from “{workflow.project_name}” to "
                    f"“{self.controller.current_project_name()}”?\n\n"
                    "In-memory Create/Inspect results will be discarded. "
                    "Configure values are kept."
                ),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.controller.switch_to_current_project(workflow)
        self._refresh_all_panels()

    def _on_project_changed(self, *args) -> None:
        abandoned = False
        for workflow_id, worker in list(self._create_workers.items()):
            worker.abandon()
            workflow = self.controller.get_workflow(workflow_id)
            if workflow is not None and workflow.create_status == "running":
                self.controller.abandon_create(workflow)
                abandoned = True
        if abandoned:
            QtWidgets.QMessageBox.information(
                self,
                "Create abandoned",
                "Project changed during create. In-memory results were discarded.",
            )
        # Empty tabs follow the new project; tabs with work keep their workflow
        # project and show Switch when mismatched.
        self.controller.sync_pristine_workflows_to_current()
        self._refresh_all_panels()

    def _current_workflow_id(self) -> str | None:
        widget = self.workflow_tabs.currentWidget()
        if widget is None:
            return None
        for workflow_id, panel in self._panels.items():
            if panel is widget:
                return workflow_id
        return None

    def _on_new_workflow(self) -> None:
        self._add_workflow_tab(self.controller.new_workflow())
        self._refresh_job_banner()

    def _on_duplicate_workflow(self) -> None:
        workflow_id = self._current_workflow_id()
        if workflow_id is None:
            return
        workflow = self.controller.duplicate_workflow(workflow_id)
        self._add_workflow_tab(workflow)
        self._refresh_job_banner()

    def _on_close_current_workflow(self) -> None:
        workflow_id = self._current_workflow_id()
        if workflow_id is None:
            return
        self._close_workflow(workflow_id)

    def _on_tab_close_requested(self, index: int) -> None:
        widget = self.workflow_tabs.widget(index)
        if widget is None:
            return
        for workflow_id, panel in list(self._panels.items()):
            if panel is widget:
                self._close_workflow(workflow_id)
                return

    def _close_workflow(self, workflow_id: str) -> bool:
        workflow = self.controller.get_workflow(workflow_id)
        if workflow is None:
            return False
        if self.controller.should_confirm_close(workflow):
            answer = QtWidgets.QMessageBox.question(
                self,
                "Discard workflow?",
                "Discard this workflow? Unsaved configuration or unwritten create results will be lost.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return False

        worker = self._create_workers.pop(workflow_id, None)
        if worker is not None:
            worker.abandon()
            if workflow.create_status == "running":
                self.controller.abandon_create(workflow)

        panel = self._panels.pop(workflow_id, None)
        if panel is not None:
            index = self.workflow_tabs.indexOf(panel)
            if index >= 0:
                self.workflow_tabs.removeTab(index)
        self.controller.remove_workflow(workflow_id)
        self._ensure_workflow_tab()
        self._refresh_job_banner()
        return True

    def _on_current_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        widget = self.workflow_tabs.widget(index)
        for workflow_id, panel in self._panels.items():
            if panel is widget:
                self.controller.active_workflow_id = workflow_id
                break

    def _refresh_all_panels(self) -> None:
        for panel in self._panels.values():
            panel.refresh()
        self._refresh_job_banner()

    def _refresh_job_banner(self) -> None:
        self.job_banner.setText(self.controller.job_status_text())
