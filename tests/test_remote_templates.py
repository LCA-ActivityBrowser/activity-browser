"""The remote project template catalogue is fetched once per session."""

import bw2data as bd
import bw2io.remote
import pytest
from qtpy import QtCore, QtWidgets

from activity_browser import app  # noqa: F401  ABApplication before pytest-qt's QApplication
from activity_browser.bwutils.commontasks import fetch_remote_projects


@pytest.fixture
def catalogue_requests(monkeypatch):
    """Replace the online catalogue with a fake one and count the requests."""
    requests = []

    def fake_get_projects(*args, **kwargs):
        requests.append(1)
        return {"forwast": "forwast.tar.gz"}

    monkeypatch.setattr(bw2io.remote, "get_projects", fake_get_projects)
    fetch_remote_projects.cache_clear()
    yield requests
    fetch_remote_projects.cache_clear()


def test_project_switch_does_not_refetch(catalogue_requests, basic_database):
    qapp = QtWidgets.QApplication.instance()
    fetch_remote_projects()
    catalogue_requests.clear()

    original = bd.projects.current
    bd.projects.create_project("template_cache_other")
    try:
        bd.projects.set_current("template_cache_other")
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
    finally:
        bd.projects.set_current(original)
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

    assert catalogue_requests == []


def test_refresh_after_failed_fetch(monkeypatch, catalogue_requests, main_window):
    from activity_browser.app.menu_bar import ProjectNewTemplateMenu
    from activity_browser.app.pages.settings import ProjectManagerSettingsChapter

    online = bw2io.remote.get_projects

    def offline(*args, **kwargs):
        catalogue_requests.append(1)
        raise ConnectionError("offline")

    monkeypatch.setattr(bw2io.remote, "get_projects", offline)
    chapter = ProjectManagerSettingsChapter(main_window)
    chapter.sync()
    menu = ProjectNewTemplateMenu(main_window)
    assert "forwast" not in chapter.template_model.df["name"].tolist()
    assert "forwast" not in menu.actions

    monkeypatch.setattr(bw2io.remote, "get_projects", online)
    chapter.refresh_templates()
    menu.aboutToShow.emit()

    # 2, not 3: the menu reused the cached failed fetch instead of asking again.
    assert len(catalogue_requests) == 2
    assert "forwast" in chapter.template_model.df["name"].tolist()
    assert "forwast" in menu.actions
