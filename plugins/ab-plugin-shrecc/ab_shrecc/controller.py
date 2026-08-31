# -*- coding: utf-8 -*-
"""SHRECC plugin workflow state (testable without Qt)."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .configure_model import (
    build_new_database_kwargs,
    config_fingerprint,
    default_config,
    is_config_complete,
    merge_config_update,
    normalize_config,
)

CreateStatus = Literal["idle", "running", "done", "failed", "stale"]
WriteStatus = Literal["idle", "running", "done", "failed"]
GlobalJob = Literal["create", "write"]


@dataclass
class WorkflowState:
    id: str
    label: str
    project_name: str
    config: dict[str, Any] = field(default_factory=dict)
    create_status: CreateStatus = "idle"
    write_status: WriteStatus = "idle"
    inspect_artifacts: dict[str, Any] = field(default_factory=dict)
    dirty: bool = False
    create_succeeded_unwritten: bool = False
    config_fingerprint_at_create: Optional[str] = None
    create_handle: Any = None
    create_error: str = ""
    written_database_names: dict[int, str] = field(default_factory=dict)
    partial_written_names: dict[int, str] = field(default_factory=dict)
    write_error: str = ""


class ShreccPluginController:
    """In-session workflow tabs and plugin-wide job lock (skeleton)."""

    def __init__(self, *, project_name_provider=None):
        self._project_name_provider = project_name_provider or _default_project_name
        self.workflows: list[WorkflowState] = []
        self.active_workflow_id: Optional[str] = None
        self.global_job: Optional[GlobalJob] = None
        self.global_job_workflow_id: Optional[str] = None
        self._label_counter = 0

    def current_project_name(self) -> str:
        return self._project_name_provider()

    def new_workflow(self) -> WorkflowState:
        self._label_counter += 1
        workflow = WorkflowState(
            id=str(uuid.uuid4()),
            label=f"Workflow {self._label_counter}",
            project_name=self.current_project_name(),
        )
        self.workflows.append(workflow)
        self.active_workflow_id = workflow.id
        return workflow

    def duplicate_workflow(self, source_id: str) -> WorkflowState:
        source = self.get_workflow(source_id)
        if source is None:
            raise KeyError(source_id)
        self._label_counter += 1
        workflow = WorkflowState(
            id=str(uuid.uuid4()),
            label=f"Workflow {self._label_counter}",
            project_name=self.current_project_name(),
            config=copy.deepcopy(source.config),
            dirty=bool(source.config),
        )
        self.workflows.append(workflow)
        self.active_workflow_id = workflow.id
        return workflow

    def remove_workflow(self, workflow_id: str) -> None:
        self.workflows = [w for w in self.workflows if w.id != workflow_id]
        if self.active_workflow_id == workflow_id:
            self.active_workflow_id = self.workflows[-1].id if self.workflows else None
        if self.global_job_workflow_id == workflow_id:
            self.global_job = None
            self.global_job_workflow_id = None

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow
        return None

    def should_confirm_close(self, workflow: WorkflowState) -> bool:
        return workflow.dirty or workflow.create_succeeded_unwritten

    def is_project_stale(self, workflow: WorkflowState) -> bool:
        return workflow.project_name != self.current_project_name()

    def is_pristine(self, workflow: WorkflowState) -> bool:
        """True when the tab has no meaningful work tied to its workflow project."""
        if workflow.dirty or workflow.create_succeeded_unwritten:
            return False
        if workflow.create_handle is not None:
            return False
        if workflow.create_status in ("running", "done", "stale"):
            return False
        if workflow.write_status in ("running", "done", "failed"):
            return False
        if self.global_job_workflow_id == workflow.id:
            return False
        return True

    def switch_to_current_project(self, workflow: WorkflowState) -> bool:
        """Rebind workflow to the current Brightway project.

        Clears in-memory create/write results (they belong to the old project).
        Keeps Configure values. Returns True when the workflow project changed.
        """
        current = self.current_project_name()
        if workflow.project_name == current:
            return False
        if workflow.create_status == "running" or workflow.write_status == "running":
            raise RuntimeError("Cannot switch project while a job is running.")
        workflow.project_name = current
        workflow.create_status = "idle"
        workflow.write_status = "idle"
        workflow.create_succeeded_unwritten = False
        workflow.inspect_artifacts = {}
        workflow.create_handle = None
        workflow.create_error = ""
        workflow.config_fingerprint_at_create = None
        workflow.written_database_names = {}
        workflow.partial_written_names = {}
        workflow.write_error = ""
        return True

    def sync_pristine_workflows_to_current(self) -> list[str]:
        """Auto-rebind empty workflows to the current project. Returns updated ids."""
        updated: list[str] = []
        current = self.current_project_name()
        for workflow in self.workflows:
            if not self.is_pristine(workflow):
                continue
            if workflow.project_name == current:
                continue
            workflow.project_name = current
            updated.append(workflow.id)
        return updated

    def job_status_text(self) -> str:
        if self.global_job is None:
            return "App job: idle"
        workflow = self.get_workflow(self.global_job_workflow_id or "")
        name = workflow.label if workflow else "?"
        return f"App job: {self.global_job} in {name}…"

    def get_config(self, workflow: WorkflowState) -> dict[str, Any]:
        if workflow.config:
            return normalize_config(workflow.config)
        return default_config()

    def update_config(self, workflow: WorkflowState, update: dict[str, Any]) -> None:
        workflow.config = merge_config_update(workflow.config, update)
        workflow.dirty = True
        self._maybe_mark_inspect_stale(workflow)

    def _maybe_mark_inspect_stale(self, workflow: WorkflowState) -> None:
        if workflow.create_status not in ("done", "stale"):
            return
        if workflow.config_fingerprint_at_create is None:
            return
        current = config_fingerprint(self.get_config(workflow))
        if current != workflow.config_fingerprint_at_create:
            self.mark_inspect_stale(workflow)

    def mark_inspect_stale(self, workflow: WorkflowState) -> None:
        """Mark configuration mismatch; keep last Inspect artifacts for review."""
        workflow.create_status = "stale"
        workflow.create_succeeded_unwritten = False
        workflow.create_handle = None
        workflow.create_error = ""

    def is_inspect_stage_available(self, workflow: WorkflowState) -> bool:
        """Inspect tab enabled after Create results exist (including mismatch / failed retry)."""
        if workflow.create_status in ("done", "stale"):
            return True
        return (
            workflow.create_status == "failed"
            and bool(workflow.inspect_artifacts)
        )

    def is_write_stage_available(self, workflow: WorkflowState) -> bool:
        """Write tab enabled only for a current successful Create (not mismatch)."""
        return (
            workflow.create_status == "done" and workflow.create_handle is not None
        )

    def create_action_label(self, workflow: WorkflowState) -> str:
        if workflow.create_status in ("failed", "stale"):
            return "Create again"
        return "Create"

    def write_action_label(self, workflow: WorkflowState) -> str:
        if workflow.write_status in ("failed", "done"):
            return "Write again"
        return "Write"

    def is_config_complete(self, workflow: WorkflowState) -> bool:
        return is_config_complete(self.get_config(workflow))

    def can_start_create(self, workflow: WorkflowState) -> bool:
        if self.is_project_stale(workflow):
            return False
        if self.global_job is not None:
            return False
        if workflow.create_status == "running":
            return False
        return self.is_config_complete(workflow)

    def can_start_write(self, workflow: WorkflowState) -> bool:
        if self.is_project_stale(workflow):
            return False
        if self.global_job is not None:
            return False
        if workflow.write_status == "running":
            return False
        return (
            workflow.create_status == "done"
            and workflow.create_handle is not None
        )

    def begin_write(self, workflow: WorkflowState) -> None:
        workflow.write_status = "running"
        workflow.write_error = ""
        workflow.partial_written_names = {}
        self.global_job = "write"
        self.global_job_workflow_id = workflow.id

    def complete_write(self, workflow: WorkflowState, written: dict[int, str]) -> None:
        workflow.write_status = "done"
        workflow.written_database_names = dict(written)
        workflow.partial_written_names = {}
        workflow.write_error = ""
        workflow.create_succeeded_unwritten = False
        self.global_job = None
        self.global_job_workflow_id = None

    def fail_write(
        self,
        workflow: WorkflowState,
        message: str,
        partial: dict[int, str],
    ) -> None:
        workflow.write_status = "failed"
        workflow.write_error = message
        workflow.partial_written_names = dict(partial)
        if partial:
            workflow.written_database_names.update(partial)
        self.global_job = None
        self.global_job_workflow_id = None

    def begin_create(self, workflow: WorkflowState) -> None:
        workflow.create_status = "running"
        workflow.create_error = ""
        # Keep prior Inspect artifacts visible until Create completes or fails.
        workflow.create_handle = None
        workflow.create_succeeded_unwritten = False
        workflow.config_fingerprint_at_create = None
        self.global_job = "create"
        self.global_job_workflow_id = workflow.id

    def complete_create(
        self,
        workflow: WorkflowState,
        create_handle: Any,
        artifacts: dict[str, Any],
    ) -> None:
        workflow.create_handle = create_handle
        workflow.inspect_artifacts = artifacts
        workflow.config_fingerprint_at_create = config_fingerprint(
            self.get_config(workflow)
        )
        workflow.create_status = "done"
        workflow.create_succeeded_unwritten = True
        workflow.dirty = False
        workflow.create_error = ""
        self.global_job = None
        self.global_job_workflow_id = None

    def fail_create(self, workflow: WorkflowState, message: str) -> None:
        workflow.create_status = "failed"
        workflow.create_error = message
        # Keep last Inspect artifacts if Create again fails after a prior success.
        workflow.create_handle = None
        workflow.create_succeeded_unwritten = False
        workflow.config_fingerprint_at_create = None
        self.global_job = None
        self.global_job_workflow_id = None

    def abandon_create(self, workflow: WorkflowState) -> None:
        workflow.create_status = "idle"
        workflow.create_error = ""
        workflow.inspect_artifacts = {}
        workflow.create_handle = None
        workflow.create_succeeded_unwritten = False
        workflow.config_fingerprint_at_create = None
        if self.global_job_workflow_id == workflow.id:
            self.global_job = None
            self.global_job_workflow_id = None

    def build_new_database_kwargs(
        self,
        workflow: WorkflowState,
        *,
        data_dir: str | None = None,
    ) -> dict[str, Any]:
        kwargs = build_new_database_kwargs(
            self.get_config(workflow),
            project_name=workflow.project_name,
        )
        if data_dir:
            kwargs["data_dir"] = data_dir
        return kwargs


def _default_project_name() -> str:
    import bw2data as bd

    return bd.projects.current
