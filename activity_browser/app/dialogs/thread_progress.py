"""App-layer sticky-cancel progress starter for ABThread jobs."""
from __future__ import annotations

from activity_browser.ui.dialogs import ABProgressDialog


def run_thread_with_progress(title: str, thread, *, on_cancelled=None) -> None:
    """
    Show a cancellable ABProgressDialog for an ABThread and start it.

    Sticky cancel: closing after success must not look like a user cancel.
    ``on_cancelled`` runs only if the thread reported ``ab_cancel_requested``.
    """
    progress = ABProgressDialog.get_connected_dialog(title, cancellable=True)
    thread.connect_progress_dialog(progress)

    def request_cancel():
        thread.request_ab_cancel()
        progress.mark_cancelled()
        progress.setLabelText("Cancelling…")

    progress.canceled.connect(request_cancel)

    def cleanup():
        was_cancelled = thread.ab_cancel_requested()
        try:
            progress.canceled.disconnect(request_cancel)
        except (RuntimeError, TypeError):
            pass
        progress.detach()
        progress.close()
        progress.deleteLater()
        if was_cancelled and on_cancelled is not None:
            on_cancelled()

    thread.finished.connect(cleanup)
    progress.show()
    thread.start()
