"""MetaDataStore pickle sidecar: pandas major so caches do not cross majors."""
from pathlib import Path

from activity_browser.bwutils.pandas_semantics import pandas_major_version

__all__ = [
    "STAMP_FILENAME",
    "pandas_major_version",
    "write_cache_stamp",
    "read_cache_stamp",
    "cache_stamp_matches_runtime",
]

STAMP_FILENAME = "metadatastore_cache.pandas_major"


def write_cache_stamp(project_ab_path: Path, major: int | None = None) -> None:
    major = pandas_major_version() if major is None else major
    (project_ab_path / STAMP_FILENAME).write_text(str(major), encoding="utf-8")


def read_cache_stamp(project_ab_path: Path) -> int | None:
    path = project_ab_path / STAMP_FILENAME
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def cache_stamp_matches_runtime(project_ab_path: Path) -> bool:
    return read_cache_stamp(project_ab_path) == pandas_major_version()
