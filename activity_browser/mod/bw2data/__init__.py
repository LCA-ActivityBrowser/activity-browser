"""AB patches for bw2data; re-exports the upstream package API.

Importing this package applies patches to the real ``bw2data`` in place, so
``import bw2data`` and ``from activity_browser.mod import bw2data`` share the
same patched classes.
"""
from __future__ import annotations

import importlib

_upstream = importlib.import_module("bw2data")

from . import signaled_save_compat  # noqa: F401


def __getattr__(name: str):
    return getattr(_upstream, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_upstream)))
