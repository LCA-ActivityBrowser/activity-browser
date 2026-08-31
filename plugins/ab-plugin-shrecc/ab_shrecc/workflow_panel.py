# -*- coding: utf-8 -*-
"""Single SHRECC workflow: stage tabs (shell placeholders)."""
from __future__ import annotations

from qtpy import QtWidgets

from . import ids
from .controller import WorkflowState


class WorkflowPanel(QtWidgets.QWidget):
    def __init__(self, workflow: WorkflowState, parent=None):
        super().__init__(parent)
        self.workflow = workflow

        layout = QtWidgets.QVBoxLayout(self)
        self.project_label = QtWidgets.QLabel()
        layout.addWidget(self.project_label)

        self.stage_tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.stage_tabs, 1)

        self.stage_tabs.addTab(
            self._placeholder_stage("Configure options for SHRECC NewDatabase."),
            ids.STAGE_LABELS[ids.STAGE_CONFIGURE],
        )
        self.stage_tabs.addTab(
            self._placeholder_stage("Create and inspect results (ticket 15)."),
            ids.STAGE_LABELS[ids.STAGE_CREATE_INSPECT],
        )
        self.stage_tabs.addTab(
            self._placeholder_stage("Write Brightway databases (ticket 16)."),
            ids.STAGE_LABELS[ids.STAGE_WRITE],
        )
        self.refresh()

    def _placeholder_stage(self, message: str) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        inner = QtWidgets.QVBoxLayout(widget)
        inner.addWidget(QtWidgets.QLabel(message))
        inner.addStretch()
        return widget

    def refresh(self) -> None:
        workflow = self.workflow
        stale = workflow.project_name != _current_project_name()
        suffix = " ⚠ project stale" if stale else ""
        self.project_label.setText(f"Project: {workflow.project_name}{suffix}")


def _current_project_name() -> str:
    import bw2data as bd

    return bd.projects.current
