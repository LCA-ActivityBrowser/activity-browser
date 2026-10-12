"""Regression tests for Qt sync helpers under PySide6/shiboken."""


def test_schedule_awake_sync_runs_without_thread_event_dispatcher(qtbot):
    """``schedule_awake_sync`` must not touch QThread.eventDispatcher().

    On PySide6 6.12+, that API can return a deleted wrapper (libshiboken
    RuntimeError), which broke deferred UI sync and DatabaseOpen.
    """
    from PySide6.QtWidgets import QWidget

    from activity_browser.ui.core import schedule_awake_sync

    owner = QWidget()
    qtbot.addWidget(owner)
    called: list[int] = []

    schedule_awake_sync(owner, lambda: called.append(1))
    qtbot.waitUntil(lambda: called == [1], timeout=2000)
