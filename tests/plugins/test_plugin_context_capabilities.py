"""PluginContext host capabilities (protect, after write, blocking operation)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import bw2data as bd
from bw2data.tests import bw2test

from activity_browser.plugins.context import PluginContext
from activity_browser.plugins.database_protection import (
    database_is_editing_blocked,
    is_database_protected,
    reset_database_protection_for_tests,
)


@pytest.fixture(autouse=True)
def _clear_protection():
    reset_database_protection_for_tests()
    yield
    reset_database_protection_for_tests()


def _ctx(plugin_id: str = "tests.fake_plugin") -> PluginContext:
    return PluginContext(
        plugin_id,
        application=SimpleNamespace(),
        signals=SimpleNamespace(),
        settings=SimpleNamespace(global_config={"plugins": {"enabled_plugins": [], "data": {}}}),
    )


def test_protect_databases_registers_and_releases():
    ctx = _ctx()
    assert not is_database_protected("bg-a")

    with ctx.protect_databases(["bg-a", "bg-b"], reason="SHRECC create"):
        assert is_database_protected("bg-a")
        assert is_database_protected("bg-b")

    assert not is_database_protected("bg-a")
    assert not is_database_protected("bg-b")


def test_protect_databases_releases_on_exception():
    ctx = _ctx()
    with pytest.raises(RuntimeError):
        with ctx.protect_databases(["bg-a"], reason="fail"):
            raise RuntimeError("boom")
    assert not is_database_protected("bg-a")


@bw2test
def test_database_delete_blocked_while_protected(monkeypatch):
    from activity_browser.app.actions.database import database_delete as mod

    db_name = "protect-me"
    bd.Database(db_name).register(read_only=False)

    shown: list[tuple] = []
    monkeypatch.setattr(
        mod.QtWidgets.QMessageBox,
        "information",
        lambda *args, **kwargs: shown.append(args) or mod.QtWidgets.QMessageBox.Ok,
    )
    monkeypatch.setattr(
        mod.QtWidgets.QMessageBox,
        "question",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not confirm")),
    )

    ctx = _ctx()
    with ctx.protect_databases([db_name], reason="test"):
        mod.DatabaseDelete.run([db_name])

    assert shown
    assert db_name in bd.databases


@bw2test
def test_database_is_editing_blocked_combines_read_only_and_protection():
    db_name = "combo-db"
    bd.Database(db_name).register(read_only=False)
    assert not database_is_editing_blocked(db_name)

    ctx = _ctx()
    with ctx.protect_databases([db_name], reason="hold"):
        assert database_is_editing_blocked(db_name)

    bd.databases[db_name]["read_only"] = True
    bd.databases.flush()
    assert database_is_editing_blocked(db_name)


@bw2test
def test_after_database_write_schedules_reload_and_signal(monkeypatch):
    scheduled: list[str] = []
    sent: list[str] = []

    class _Signals:
        def send(self, *, name):
            sent.append(name)

    from activity_browser.bwutils.metadata import loader

    monkeypatch.setattr(loader, "schedule_database_metadata_reload", lambda n: scheduled.append(n))

    import bw2data.signals as bw_signals

    monkeypatch.setattr(bw_signals, "on_database_write", _Signals())

    db_name = "written-db"
    bd.Database(db_name).register()

    ctx = _ctx()
    ctx.after_database_write(db_name, notify=True)
    assert scheduled == [db_name]
    assert sent == [db_name]

    scheduled.clear()
    sent.clear()
    ctx.after_database_write(db_name, notify=False)
    assert scheduled == [db_name]
    assert sent == []


def test_run_blocking_operation_success(main_window, qtbot):
    ctx = _ctx()
    result = ctx.run_blocking_operation("Write databases", lambda: 42)
    assert result == 42


def test_run_blocking_operation_raises(main_window, qtbot):
    ctx = _ctx()

    def boom():
        raise ValueError("strict mapping failed")

    with pytest.raises(ValueError, match="strict mapping failed"):
        ctx.run_blocking_operation("Write databases", boom)


def test_safe_bw_connection_exported_and_usable(monkeypatch):
    """Do not enter the real SafeBWConnection on the test thread (closes peewee)."""
    from activity_browser.plugins import safe_bw_connection

    calls: list[str] = []

    class _FakeSafeBW:
        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *args):
            calls.append("exit")
            return False

    monkeypatch.setattr(
        "activity_browser.ui.core.threading.SafeBWConnection",
        _FakeSafeBW,
    )

    with safe_bw_connection():
        pass
    assert calls == ["enter", "exit"]

    ctx = _ctx()
    with ctx.safe_bw_connection():
        pass
    assert calls == ["enter", "exit", "enter", "exit"]
