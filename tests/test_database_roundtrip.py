"""Database export/import round-trip tests (sqlite & functional_sqlite)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest
from bw2data.tests import bw2test
from bw2io import create_core_migrations, create_default_biosphere3

from activity_browser.bwutils.exporters import database_has_parameters
from activity_browser.bwutils.metadata.loader import MDSLoader
from activity_browser.bwutils.metadata.metadata import MetaDataStore
from fixtures.database_roundtrip import (
    compare_databases_semantically,
    roundtrip_import,
    visible_product_count,
    write_source_db,
)

BACKENDS = [
    ("sqlite", "sqlite"),
    ("functional_sqlite", "functional"),
]
FORMATS = ["bw2package", "excel"]


def project_setup() -> None:
    create_core_migrations()
    create_default_biosphere3()


@bw2test
@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("backend,kind", BACKENDS)
@pytest.mark.parametrize("parameters", [False, True], ids=["no_params", "with_params"])
def test_database_roundtrip(backend, kind, fmt, parameters):
    project_setup()
    source = f"roundtrip_{kind}_{fmt}_{'params' if parameters else 'noparams'}"

    import bw2data as bd

    write_source_db(source, kind, parameters=parameters)
    assert bd.databases[source].get("backend") == backend
    if parameters:
        assert database_has_parameters(source)

    with tempfile.TemporaryDirectory() as tmp:
        target = roundtrip_import(source, fmt, tmp)

    assert compare_databases_semantically(source, target) == []
    if kind == "functional":
        assert visible_product_count(target) == 2

    if parameters:
        if fmt == "excel":
            assert database_has_parameters(target)
        else:
            assert not database_has_parameters(target)


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
