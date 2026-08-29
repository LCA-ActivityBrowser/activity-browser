"""Regression: MetaDataStore singleton must stay aligned with app.metadata."""

from activity_browser import app
from activity_browser.bwutils.metadata.metadata import MetaDataStore


def test_metadata_singleton_matches_app(basic_database):
    assert MetaDataStore._instance is app.metadata

    process = basic_database.get("process")
    meta = app.metadata.get_metadata([process.key], ["name", "product"])
    assert not meta.empty
    assert meta.iloc[0]["name"] == process["name"]
