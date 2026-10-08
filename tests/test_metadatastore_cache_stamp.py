"""MetaDataStore pickle cache stamp: invalidate across pandas majors."""
from pathlib import Path

import pandas as pd

from activity_browser.bwutils.metadata.metadata import (
    CACHE_PICKLE_NAME,
    MetaDataStore,
    dataframe_for_pickle_cache,
    pandas_major_version,
    read_cache_stamp,
    write_cache_stamp,
    cache_stamp_matches_runtime,
    clear_cache_files,
)


def test_dataframe_for_pickle_cache_strips_string_dtype():
    df = pd.DataFrame({"name": pd.Series(["a", "b"], dtype="string")})
    out = dataframe_for_pickle_cache(df)
    assert not isinstance(out["name"].dtype, pd.StringDtype)


def test_write_and_read_cache_stamp(tmp_path: Path):
    major = pandas_major_version()
    write_cache_stamp(tmp_path, major)
    assert read_cache_stamp(tmp_path) == major


def test_cache_stamp_matches_runtime_when_equal(tmp_path: Path):
    write_cache_stamp(tmp_path, pandas_major_version())
    assert cache_stamp_matches_runtime(tmp_path) is True


def test_cache_stamp_mismatch_when_wrong_major(tmp_path: Path):
    write_cache_stamp(tmp_path, pandas_major_version() + 1)
    assert cache_stamp_matches_runtime(tmp_path) is False


def test_missing_cache_stamp_does_not_match(tmp_path: Path):
    assert cache_stamp_matches_runtime(tmp_path) is False


def test_clear_cache_files_removes_pickle_and_stamp(tmp_path: Path):
    pickle_path = tmp_path / CACHE_PICKLE_NAME
    pickle_path.write_bytes(b"x")
    write_cache_stamp(tmp_path, pandas_major_version())
    clear_cache_files(tmp_path)
    assert not pickle_path.exists()
    assert read_cache_stamp(tmp_path) is None


def test_flush_writes_pickle_and_stamp(monkeypatch, tmp_path: Path):
    """Flush with caching enabled writes both pickle and pandas-major stamp."""
    from activity_browser.bwutils import filesystem
    from activity_browser.bwutils.settings import Settings

    monkeypatch.setattr(filesystem, "get_project_ab_path", lambda: tmp_path)
    settings = Settings()
    previous = settings["metadatastore"]["caching_enabled"]
    settings["metadatastore"]["caching_enabled"] = True

    mds = MetaDataStore()
    old_df = mds._dataframe
    old_added, old_updated, old_deleted = mds._added.copy(), mds._updated.copy(), mds._deleted.copy()
    try:
        mds._dataframe = pd.DataFrame({"name": ["x"]})
        mds._added = {("db", "code")}
        mds._updated = set()
        mds._deleted = set()
        mds.flush_mutations()
        assert (tmp_path / CACHE_PICKLE_NAME).is_file()
        assert read_cache_stamp(tmp_path) == pandas_major_version()
    finally:
        mds._dataframe = old_df
        mds._added, mds._updated, mds._deleted = old_added, old_updated, old_deleted
        settings["metadatastore"]["caching_enabled"] = previous


def test_has_cache_false_when_stamp_mismatches(monkeypatch, tmp_path: Path):
    """Loader ignores a pickle whose stamp does not match the running pandas major."""
    from activity_browser.bwutils import filesystem

    (tmp_path / CACHE_PICKLE_NAME).write_bytes(b"x")
    write_cache_stamp(tmp_path, pandas_major_version() + 1)
    lci = tmp_path / "lci"
    lci.mkdir()
    (lci / "databases.db").write_bytes(b"x")

    monkeypatch.setattr(filesystem, "get_project_ab_path", lambda: tmp_path)
    monkeypatch.setattr(filesystem, "get_project_path", lambda: tmp_path)

    assert MetaDataStore().loader._has_cache() is False
