"""INFO→progress bridge must emit int progress, never None (Shiboken-safe)."""
from __future__ import annotations

import threading
from types import SimpleNamespace

from activity_browser.ui.core.threading import LoggingProgressSink, thread_local


class _Record(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def test_logging_progress_sink_emits_indeterminate_progress_not_none():
    calls = []
    thread_local.progress_slot = lambda progress, message: calls.append(
        (progress, message)
    )

    sink = LoggingProgressSink("INFO")
    record = _Record(
        level=SimpleNamespace(name="INFO"),
        thread=SimpleNamespace(id=threading.get_ident()),
        message="Extracting .7z archive to memory",
    )
    sink(SimpleNamespace(record=record))

    assert calls == [(-1, "Extracting .7z archive to memory")]
    assert isinstance(calls[0][0], int)
