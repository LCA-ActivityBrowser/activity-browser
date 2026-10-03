"""Metadata reload after worker-thread database writes."""

from __future__ import annotations

import sqlite3

import bw2data as bd
from bw2data.backends import sqlite3_lci_db
from bw2data.parameters import ParameterizedExchange
from bw2data.tests import bw2test

from activity_browser import app
from activity_browser.bwutils.commontasks import count_database_records
from activity_browser.ui.core.threading import ABThread
from fixtures.basic import DATABASE
from fixtures.bw_helpers import write_functional_database


def _sqlite_activity_count(db_name: str) -> int:
    with sqlite3.connect(sqlite3_lci_db._filepath) as con:
        return con.execute(
            "SELECT COUNT(*) FROM activitydataset WHERE database = ?",
            (db_name,),
        ).fetchone()[0]


def _wait_metadata_count(qtbot, db_name: str, expected: int, timeout_ms: int = 10_000) -> None:
    for _ in range(timeout_ms // 50):
        if count_database_records(db_name) == expected:
            return
        qtbot.wait(50)
    assert count_database_records(db_name) == expected


@bw2test
def test_metadata_loads_after_worker_thread_duplicate(main_window, basic_database, qtbot):
    """Duplicate in ABThread must populate MetaDataStore without F5."""
    source = basic_database.name
    target = "copy_after_worker_write"
    source_count = count_database_records(source)

    class DuplicateThread(ABThread):
        def run_safely(self):
            db = bd.Database(source)
            data = db.relabel_data(db.load(), source, target)
            new_db = bd.Database(target, backend="functional_sqlite")
            new_db.register(write_empty=False)
            new_db.write(data, signal=True)

    thread = DuplicateThread(app.application)
    thread.start()
    with qtbot.waitSignal(thread.finished, timeout=60_000):
        pass

    assert len(bd.Database(target)) == source_count
    assert _sqlite_activity_count(target) == source_count
    _wait_metadata_count(qtbot, target, source_count)


@bw2test
def test_signaling_write_on_main_thread_updates_metadata_and_index(
    main_window, qtbot
):
    """Unguarded signaling write rebuilds parameterized flows and reloads MDS."""
    write_functional_database("basic", DATABASE, process=True)
    ParameterizedExchange.delete().execute()
    assert ParameterizedExchange.select().count() == 0

    db = bd.Database("basic")
    data = db.load()
    db.write(data, signal=True)

    assert [row.formula for row in ParameterizedExchange.select()] == ["5+5"]
    _wait_metadata_count(qtbot, "basic", len(bd.Database("basic")))


def test_secondary_load_reconnect_does_not_warn(qapp, basic_database):
    """Reloading metadata must not warn about disconnecting an unconnected slot."""
    import warnings

    from activity_browser.app import metadata

    loader = metadata.loader
    assert loader.secondary_status == "done"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        loader._begin_secondary_load(
            [basic_database.name], loader.secondary_load_database
        )
        qapp.processEvents()

    assert not any("Failed to disconnect" in str(w.message) for w in caught)
