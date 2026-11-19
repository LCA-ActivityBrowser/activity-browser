"""Regression: in-memory ecoinvent .7z extract via py7zr >= 1.0 factory API."""
from __future__ import annotations

from pathlib import Path

import py7zr

from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter


def test_read_archive_to_bytes_roundtrip(tmp_path):
    content = b'<?xml version="1.0"?><root>spold</root>'
    datasets = tmp_path / "datasets"
    datasets.mkdir()
    spold = datasets / "a.spold"
    spold.write_bytes(content)
    archive_path = tmp_path / "ecoinvent.7z"
    with py7zr.SevenZipFile(archive_path, "w") as z:
        z.write(spold, "datasets/a.spold")

    data = Ecoinvent7zImporter(str(archive_path)).read_archive_to_bytes()

    assert list(data) == ["datasets/a.spold"]
    assert data["datasets/a.spold"].getvalue() == content
