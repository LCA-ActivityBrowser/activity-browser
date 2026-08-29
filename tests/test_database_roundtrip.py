"""AB metadata loading after Excel database import (bw2io round-trip covered upstream)."""

from __future__ import annotations

import tempfile
import time

from bw2data.tests import bw2test
from bw2io import create_core_migrations, create_default_biosphere3

from activity_browser.bwutils.metadata.metadata import MetaDataStore
from fixtures.database_roundtrip import roundtrip_import, visible_product_count, write_source_db


def project_setup() -> None:
    create_core_migrations()
    create_default_biosphere3()


def _teardown_temporary_mds(mds: MetaDataStore) -> None:
    """Stop loader threads and disconnect bw2data signals before dropping the instance."""
    from bw2data import signals
    from bw2data.meta import databases

    loader = getattr(mds, "loader", None)
    if loader is not None:
        if loader.thread is not None and loader.thread.isRunning():
            loader.thread.wait(10_000)
        try:
            signals.project_changed.disconnect(loader.on_project_changed)
        except (TypeError, RuntimeError):
            pass
        loader._disconnect_thread_results()

    updater = getattr(mds, "updater", None)
    if updater is not None:
        for signal, slot in (
            (signals.signaleddataset_on_save, updater.on_signaleddataset_save),
            (signals.signaleddataset_on_delete, updater.on_signaleddataset_delete),
            (signals.on_database_delete, updater.on_database_deleted_bw),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        try:
            databases._save_signal.disconnect(updater.on_databases_metadata_change)
        except (TypeError, RuntimeError, AttributeError):
            pass


@bw2test
def test_load_database_populates_metadata_for_excel_import(qapp, monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.metadata.updater.MDSUpdater.connect_signals",
        lambda self: None,
    )
    previous_instance = MetaDataStore._instance
    temp_mds = None
    try:
        MetaDataStore._instance = None
        project_setup()
        source = "roundtrip_metadata_src"
        write_source_db(source, "functional")

        temp_mds = MetaDataStore()
        # Use the loader owned by the store — a second MDSLoader would also
        # connect to bw2data.project_changed and crash later @bw2test fixtures.
        loader = temp_mds.loader

        with tempfile.TemporaryDirectory() as tmp:
            target = roundtrip_import(source, "excel", tmp)

        assert temp_mds.get_database_metadata(target, ["name"]).empty
        loader.load_database(target)
        for _ in range(100):
            if loader.secondary_status == "done":
                break
            time.sleep(0.05)
            qapp.processEvents()

        assert len(temp_mds.get_database_metadata(target, ["name", "processor", "type"])) == 4
        assert visible_product_count(target) == 2
    finally:
        if temp_mds is not None:
            _teardown_temporary_mds(temp_mds)
        MetaDataStore._instance = previous_instance
