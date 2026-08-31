# -*- coding: utf-8 -*-
"""SHRECC plugin workflow state (testable without Qt)."""
from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .configure_model import (
    build_new_database_kwargs,
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

    def is_config_complete(self, workflow: WorkflowState) -> bool:
        return is_config_complete(self.get_config(workflow))

    def can_start_create(self, workflow: WorkflowState) -> bool:
        if self.is_project_stale(workflow):
            return False
        if self.global_job is not None:
            return False
        return self.is_config_complete(workflow)

    def build_new_database_kwargs(self, workflow: WorkflowState) -> dict[str, Any]:
        return build_new_database_kwargs(
            self.get_config(workflow),
            project_name=workflow.project_name,
        )


def _default_project_name() -> str:
    import bw2data as bd

    return bd.projects.current
