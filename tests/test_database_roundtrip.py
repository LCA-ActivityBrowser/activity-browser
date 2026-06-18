"""AB metadata loading after Excel database import (bw2io round-trip covered upstream)."""

from __future__ import annotations

import tempfile
import time

from bw2data.tests import bw2test
from bw2io import create_core_migrations, create_default_biosphere3

from activity_browser.bwutils.metadata.loader import MDSLoader
from activity_browser.bwutils.metadata.metadata import MetaDataStore
from fixtures.database_roundtrip import roundtrip_import, visible_product_count, write_source_db


def project_setup() -> None:
    create_core_migrations()
    create_default_biosphere3()


@bw2test
def test_load_database_populates_metadata_for_excel_import(qapp, monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.metadata.updater.MDSUpdater.connect_signals",
        lambda self: None,
    )
    MetaDataStore._instance = None
    project_setup()
    source = "roundtrip_metadata_src"
    write_source_db(source, "functional")

    mds = MetaDataStore()
    loader = MDSLoader(mds)

    with tempfile.TemporaryDirectory() as tmp:
        target = roundtrip_import(source, "excel", tmp)

    assert mds.get_database_metadata(target, ["name"]).empty
    loader.load_database(target)
    for _ in range(100):
        if loader.secondary_status == "done":
            break
        time.sleep(0.05)
        qapp.processEvents()

    assert len(mds.get_database_metadata(target, ["name", "processor", "type"])) == 4
    assert visible_product_count(target) == 2
