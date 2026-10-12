"""Startup project activation before UI project.changed listeners."""
from __future__ import annotations

from pathlib import Path

import bw2data as bd

# ABApplication before pytest-qt's QApplication (see tests/conftest.py / other UI tests).
from activity_browser import app  # noqa: F401
from activity_browser.bwutils.settings import Settings, activate_configured_project


def test_activate_configured_project_noops_when_already_current(monkeypatch):
    settings = Settings()
    settings.global_config.setdefault("startup", {})
    settings.global_config["startup"]["brightway_directory"] = str(
        bd.projects._base_data_dir
    )
    settings.global_config["startup"]["startup_project"] = bd.projects.current

    calls: list = []
    monkeypatch.setattr(
        bd.projects,
        "change_base_directories",
        lambda *a, **k: calls.append(1),
    )

    assert activate_configured_project(settings) is False
    assert calls == []


def test_activate_configured_project_switches_when_needed(monkeypatch):
    settings = Settings()
    settings.global_config.setdefault("startup", {})
    settings.global_config["startup"]["brightway_directory"] = str(
        bd.projects._base_data_dir
    )
    settings.global_config["startup"]["startup_project"] = "__startup_other__"

    calls: list = []

    def _switch(base_dir, project_name=None, update=True, **kwargs):
        calls.append(
            {
                "base_dir": Path(base_dir),
                "project_name": project_name,
                "update": update,
            }
        )

    monkeypatch.setattr(bd.projects, "change_base_directories", _switch)

    assert activate_configured_project(settings) is True
    assert len(calls) == 1
    assert calls[0]["project_name"] == "__startup_other__"
    assert calls[0]["update"] is False


def test_apply_settings_skips_project_switch_when_already_active(
    main_window, monkeypatch
):
    """When dir+project already match settings, do not call set_current again."""
    app.settings.global_config.setdefault("startup", {})
    app.settings.global_config["startup"]["brightway_directory"] = str(
        bd.projects._base_data_dir
    )
    app.settings.global_config["startup"]["startup_project"] = bd.projects.current

    switch_calls: list = []
    sync_calls: list = []

    monkeypatch.setattr(
        bd.projects,
        "change_base_directories",
        lambda *a, **k: switch_calls.append(1),
    )
    monkeypatch.setattr(app.main_window, "sync", lambda: sync_calls.append(1))
    monkeypatch.setattr(app.application, "apply_color_scheme", lambda *a, **k: None)

    app.main_window.apply_settings(load=True)

    assert switch_calls == []
    assert sync_calls == [1]


def test_apply_settings_switches_when_project_differs(main_window, monkeypatch):
    """load=True still switches when the startup project name differs."""
    app.settings.global_config.setdefault("startup", {})
    app.settings.global_config["startup"]["brightway_directory"] = str(
        bd.projects._base_data_dir
    )
    app.settings.global_config["startup"]["startup_project"] = "__not_the_current__"

    switch_calls: list = []
    monkeypatch.setattr(
        bd.projects,
        "change_base_directories",
        lambda *a, **k: switch_calls.append((a, k)),
    )
    monkeypatch.setattr(app.main_window, "sync", lambda: None)
    monkeypatch.setattr(app.application, "apply_color_scheme", lambda *a, **k: None)
    monkeypatch.setattr(
        app.actions.ProjectSwitch, "set_warning_bar", staticmethod(lambda: None)
    )

    app.main_window.apply_settings(load=True)

    assert len(switch_calls) == 1
