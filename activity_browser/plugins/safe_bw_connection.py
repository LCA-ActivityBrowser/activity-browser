# -*- coding: utf-8 -*-
"""Thread-safe Brightway connection cleanup for plugin workers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def safe_bw_connection() -> Iterator[None]:
    """Close Brightway/peewee SQLite connections for this thread on exit.

    Use in plugin worker threads that touch Brightway so connections opened on
    the worker do not leak or confuse other threads.
    """
    from activity_browser.ui.core.threading import SafeBWConnection

    with SafeBWConnection():
        yield
