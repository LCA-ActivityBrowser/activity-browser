"""SHRECC plugin integration smoke (mocked NewDatabase, no network)."""
from __future__ import annotations

from contextlib import contextmanager
from importlib.metadata import entry_points

import pandas as pd
import pytest
from qtpy import QtCore

from activity_browser import app  # noqa: F401 — ABApplication before pytest-qt's QApplication


def _shrecc_installed():
    return any(
        ep.name == "ab_shrecc"
        for ep in entry_points(group="activity_browser.plugins")
    )


pytestmark = pytest.mark.skipif(
    not _shrecc_installed(),
    reason="Install with: pip install -e ./plugins/ab-plugin-shrecc",
)


class _RecordingHost:
    def __init__(self) -> None:
        self.protected_batches: list[list[str]] = []
        self.after_write_calls: list[str] = []
        self.blocking_titles: list[str] = []

    @contextmanager
    def protect_databases(self, names, *, reason="SHRECC create"):
        self.protected_batches.append(list(names))
        yield

    def after_database_write(self, db_name: str, *, notify: bool = True) -> None:
        self.after_write_calls.append(db_name)

    def run_blocking_operation(self, title, func, *, cancellable: bool = False):
        self.blocking_titles.append(title)
        return func()


class _MockNewDatabase:
    years = [2021]
    database_names = {2021: "shrecc_out"}
    sources = {2021: "energy_charts"}
    background_databases = {2021: "bg-db"}
    mapping_gap_reports = {2021: pd.DataFrame()}
    written_database_names = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def create(self) -> None:
        self.created = True

    def write(self) -> None:
        self.written_database_names = {2021: "shrecc_out"}

    def mapping_report(self, year):
        return pd.DataFrame()

    def table(self, year):
        return pd.DataFrame({"DE": [1.0]}, index=["electricity"])


class _SyncCreateWorker(QtCore.QObject):
    """Runs mocked create synchronously (no thread) for integration tests."""

    completed = QtCore.Signal(object, dict)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, kwargs, host, *, new_database_factory=None, parent=None):
        super().__init__(parent)
        self._kwargs = kwargs
        self._host = host
        self._factory = new_database_factory or (lambda **kw: _MockNewDatabase(**kw))

    def abandon(self) -> None:
        pass

    def start(self) -> None:
        from ab_shrecc.configure_model import background_database_names_from_kwargs
        from ab_shrecc.create_service import run_create

        names = background_database_names_from_kwargs(self._kwargs)
        try:
            with self._host.protect_databases(names):
                ndb, result = run_create(
                    self._kwargs,
                    new_database_factory=self._factory,
                )
            self.completed.emit(ndb, result.artifacts)
        except BaseException as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


def _complete_config(page):
    workflow = page.controller.workflows[0]
    page.controller.update_config(
        workflow,
        {
            "years": [2021],
            "countries": ["DE"],
            "time_range_start": "2021-01-01 00:00:00",
            "time_range_end": "2021-12-31 23:00:00",
            "bg_db_name": "bg-db",
        },
    )
    workflow.output_db_base_name = "shrecc_out"
    page._refresh_all_panels()
    return workflow


@pytest.fixture
def recording_host():
    return _RecordingHost()


def test_happy_path_configure_create_inspect_write(qtbot, monkeypatch, recording_host):
    monkeypatch.setattr("ab_shrecc.page.CreateWorker", _SyncCreateWorker)

    from ab_shrecc.page import ShreccPluginPage

    page = ShreccPluginPage(host=recording_host)
    qtbot.addWidget(page)
    page.show()

    workflow = _complete_config(page)
    panel = page._panels[workflow.id]

    assert panel.create_btn.isEnabled()
    page._start_create(workflow.id)
    qtbot.waitUntil(lambda: workflow.create_status == "done", timeout=5000)

    assert workflow.inspect_artifacts.get("summary")
    assert panel.stage_tabs.isTabEnabled(panel._inspect_index)
    assert panel.stage_tabs.isTabEnabled(panel._write_index)
    assert panel.stage_tabs.currentIndex() == panel._inspect_index
    assert panel.write_panel.write_btn.isEnabled()
    assert panel.create_btn.text() == "Create"

    page._start_write(workflow.id)

    assert workflow.write_status == "done"
    assert workflow.written_database_names == {2021: "shrecc_out"}
    assert recording_host.protected_batches == [["bg-db"]]
    assert recording_host.after_write_calls == ["shrecc_out"]
    assert recording_host.blocking_titles == ["Writing SHRECC databases"]


def test_open_shrecc_action_registered():
    from ab_shrecc.actions import OpenShreccPage
    from ab_shrecc import ids

    assert OpenShreccPage.text == "Open SHRECC"
    assert ids.SHOW_PAGE == "ab_shrecc.show_page"
