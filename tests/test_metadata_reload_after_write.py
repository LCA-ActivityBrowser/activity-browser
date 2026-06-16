"""Metadata reload after worker-thread database writes."""

from __future__ import annotations

import sqlite3

import bw2data as bd
import pytest
from bw2data.backends import sqlite3_lci_db
from bw2data.tests import bw2test

from activity_browser import app
from activity_browser.bwutils.commontasks import count_database_records
from activity_browser.ui.core.threading import ABThread


def _sqlite_activity_count(db_name: str) -> int:
    with sqlite3.connect(sqlite3_lci_db._filepath) as con:
        return con.execute(
            "SELECT COUNT(*) FROM activitydataset WHERE database = ?",
            (db_name,),
        ).fetchone()[0]


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
            new_db.write(data)

    thread = DuplicateThread(app.application)
    thread.start()
    with qtbot.waitSignal(thread.finished, timeout=60_000):
        pass

    assert len(bd.Database(target)) == source_count
    assert _sqlite_activity_count(target) == source_count

    for _ in range(200):
        if count_database_records(target) == source_count:
            break
        qtbot.wait(50)

    assert count_database_records(target) == source_count
