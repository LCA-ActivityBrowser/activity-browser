"""Pandas-major sidecar invalidates the MetaDataStore pickle across majors."""
from pathlib import Path

from activity_browser.bwutils.metadata.cache import (
    pandas_major_version,
    read_cache_stamp,
    write_cache_stamp,
    cache_stamp_matches_runtime,
)
from activity_browser.bwutils.pandas_semantics import pandas_major_version as runtime_major


def test_write_and_read_cache_stamp(tmp_path: Path):
    major = pandas_major_version()
    write_cache_stamp(tmp_path, major)
    assert read_cache_stamp(tmp_path) == major


def test_cache_stamp_matches_runtime_when_equal(tmp_path: Path):
    write_cache_stamp(tmp_path, runtime_major())
    assert cache_stamp_matches_runtime(tmp_path) is True


def test_cache_stamp_mismatch_when_wrong_major(tmp_path: Path):
    write_cache_stamp(tmp_path, runtime_major() + 1)
    assert cache_stamp_matches_runtime(tmp_path) is False


def test_missing_cache_stamp_does_not_match(tmp_path: Path):
    assert cache_stamp_matches_runtime(tmp_path) is False
