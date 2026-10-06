"""Explorer session discovery, Prepare, and Plugin job gating (Qt-free)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ab_shrecc.controller import ShreccPluginController
from ab_shrecc.explorer_session import (
    ENV_EXPORTS_DIR,
    ExplorerSession,
    explorer_exports_dir,
)


def _write_manifest(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "manifest.json").write_text(
        '{"format": "shrecc-consumption-results", "version": 1, "chunks": []}',
        encoding="utf-8",
    )


def test_status_empty_when_no_cache_and_no_exports(tmp_path: Path):
    session = ExplorerSession(data_dir_provider=lambda: tmp_path)
    status = session.status()
    assert status.data_dir == tmp_path
    assert status.data_dir_ok
    assert not status.has_cache
    assert status.ready_exports == []
    assert not status.can_prepare
    assert not status.can_embed


def test_status_can_prepare_when_cache_present_without_exports(tmp_path: Path):
    _write_manifest(tmp_path / "2025" / "consumption_results_v1")
    session = ExplorerSession(data_dir_provider=lambda: tmp_path)
    status = session.status()
    assert status.has_cache
    assert status.can_prepare
    assert not status.can_embed


def test_status_can_embed_when_export_exists(tmp_path: Path):
    exports = explorer_exports_dir(tmp_path)
    exports.mkdir(parents=True)
    nc = exports / "shrecc_2025_eu_countries.nc"
    nc.write_bytes(b"netcdf-placeholder")
    session = ExplorerSession(data_dir_provider=lambda: tmp_path)
    status = session.status()
    assert status.can_embed
    assert nc.resolve() in {p.resolve() for p in status.ready_exports}


def test_ensure_server_raises_when_not_ready(tmp_path: Path):
    session = ExplorerSession(data_dir_provider=lambda: tmp_path)
    with pytest.raises(RuntimeError):
        session.ensure_server()


def test_prepare_writes_export_via_injected_runner(tmp_path: Path):
    _write_manifest(tmp_path / "2025" / "consumption_results_v1")

    def fake_prepare(data_dir: Path, export_dir: Path) -> list[Path]:
        export_dir.mkdir(parents=True, exist_ok=True)
        out = export_dir / "shrecc_2025_eu_countries.nc"
        out.write_bytes(b"ok")
        return [out]

    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    session = ExplorerSession(
        data_dir_provider=lambda: tmp_path,
        prepare_runner=fake_prepare,
    )
    assert ctrl.can_start_prepare()
    ctrl.begin_prepare()
    written = session.run_prepare()
    ctrl.complete_prepare()
    assert written
    assert session.status().can_embed
    assert ctrl.global_job is None


def test_prepare_blocked_during_create():
    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    workflow = ctrl.new_workflow()
    ctrl.begin_create(workflow)
    assert not ctrl.can_start_prepare()
    assert ctrl.global_job == "create"


def test_create_blocked_during_prepare():
    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    workflow = ctrl.new_workflow()
    ctrl.begin_prepare()
    assert not ctrl.can_start_create(workflow)
    assert ctrl.global_job == "prepare"


def test_prepare_blocked_during_write():
    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    workflow = ctrl.new_workflow()
    ctrl.begin_write(workflow)
    assert not ctrl.can_start_prepare()
    assert ctrl.global_job == "write"


def test_write_blocked_during_prepare():
    ctrl = ShreccPluginController(project_name_provider=lambda: "p")
    workflow = ctrl.new_workflow()
    workflow.create_status = "done"
    workflow.create_handle = object()
    workflow.output_db_base_name = "out"
    ctrl.begin_prepare()
    assert not ctrl.can_start_write(workflow)


class _FakeProc:
    def __init__(self):
        self._alive = True
        self.stderr = None

    def poll(self):
        return None if self._alive else 0

    def terminate(self):
        self._alive = False

    def kill(self):
        self._alive = False

    def wait(self, timeout=None):
        self._alive = False
        return 0


def test_ensure_server_starts_once_and_reuses_url(tmp_path: Path, monkeypatch):
    exports = explorer_exports_dir(tmp_path)
    exports.mkdir(parents=True)
    (exports / "shrecc_2025_eu_countries.nc").write_bytes(b"x")

    starts = []

    def factory(command, *, env, cwd):
        starts.append((command, env[ENV_EXPORTS_DIR]))
        return _FakeProc()

    session = ExplorerSession(
        data_dir_provider=lambda: tmp_path,
        process_factory=factory,
        health_timeout_s=1.0,
    )
    monkeypatch.setattr(
        session,
        "_wait_healthy",
        lambda url: True,
    )
    url1 = session.ensure_server()
    url2 = session.ensure_server()
    assert url1 == url2
    assert url1.startswith("http://127.0.0.1:")
    assert len(starts) == 1
    assert starts[0][1] == str(exports)
    session.stop_server()
