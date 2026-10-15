"""Unit tests for activate_configured_project (no Qt / main_window)."""
from __future__ import annotations

from pathlib import Path

import bw2data as bd

from activity_browser.bwutils.settings import Settings, activate_configured_project


def _startup_settings(*, project: str) -> Settings:
    settings = Settings()
    settings.global_config.setdefault("startup", {})
    settings.global_config["startup"]["brightway_directory"] = str(
        bd.projects._base_data_dir
    )
    settings.global_config["startup"]["startup_project"] = project
    return settings


def test_activate_configured_project_noops_when_already_current(monkeypatch):
    settings = _startup_settings(project=bd.projects.current)
    calls: list = []
    monkeypatch.setattr(
        bd.projects, "change_base_directories", lambda *a, **k: calls.append(1)
    )

    assert activate_configured_project(settings) is False
    assert calls == []


def test_activate_configured_project_switches_when_needed(monkeypatch):
    settings = _startup_settings(project="__startup_other__")
    calls: list = []

    def _switch(base_dir, project_name=None, update=True, **kwargs):
        calls.append({"project_name": project_name, "update": update})

    monkeypatch.setattr(bd.projects, "change_base_directories", _switch)

    assert activate_configured_project(settings) is True
    assert calls == [{"project_name": "__startup_other__", "update": False}]
