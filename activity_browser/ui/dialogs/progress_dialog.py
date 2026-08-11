from qtpy.QtWidgets import QProgressDialog

from activity_browser.mod.tqdm import qt_tqdm
from activity_browser.mod.pyprind import qt_pyprind


class ABProgressDialog(QProgressDialog):

    @classmethod
    def get_connected_dialog(
        cls, title: str, *, cancellable: bool = False
    ) -> "ABProgressDialog":
        from activity_browser.app import application

        dialog = cls(application.main_window)
        dialog.setWindowTitle(title)
        dialog.setLabelText("Initializing")
        dialog.setRange(0, 100)
        dialog.setAutoReset(False)
        dialog.setAutoClose(False)
        dialog.setMinimumDuration(0)
        dialog._ab_cancelled = False
        dialog._updates_disconnected = False
        if cancellable:
            dialog.setCancelButtonText("Cancel")
        else:
            dialog.setCancelButton(None)

        # qt_tqdm emits (percent: int, desc: str); qt_pyprind emits (title: str, percent)
        qt_tqdm.updated.connect(dialog._receive_tqdm_update)
        qt_pyprind.updated.connect(dialog._receive_pyprind_update)
        dialog.canceled.connect(dialog._on_canceled)

        return dialog

    def _on_canceled(self):
        self.mark_cancelled()

    def mark_cancelled(self) -> None:
        """Sticky cancel flag + stop progress updates (safe after dialog close)."""
        self._ab_cancelled = True
        self.disconnect_progress_updates()

    def disconnect_progress_updates(self):
        """Idempotent: safe to call more than once (close() may re-enter via canceled)."""
        if getattr(self, "_updates_disconnected", False):
            return
        self._updates_disconnected = True
        for signal, slot in (
            (qt_tqdm.updated, self._receive_tqdm_update),
            (qt_pyprind.updated, self._receive_pyprind_update),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def detach(self):
        """Disconnect all external slots before closing after a finished job."""
        try:
            self.canceled.disconnect(self._on_canceled)
        except (RuntimeError, TypeError):
            pass
        self.disconnect_progress_updates()

    @property
    def ab_cancelled(self) -> bool:
        return bool(getattr(self, "_ab_cancelled", False) or self.wasCanceled())

    def _receive_tqdm_update(self, value: int, title: str):
        # Calling setValue after Cancel can re-show / clear canceled state in Qt.
        if self.ab_cancelled or getattr(self, "_updates_disconnected", False):
            return
        self.setRange(0, 100)
        self.setLabelText(title or "Working...")
        self.setValue(int(value))

    def _receive_pyprind_update(self, title: str, value: float):
        if self.ab_cancelled or getattr(self, "_updates_disconnected", False):
            return
        self.setRange(0, 100)
        self.setLabelText(title or "Working...")
        self.setValue(int(value))
