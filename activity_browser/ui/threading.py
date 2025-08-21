import threading
import logging

from activity_browser.mod.tqdm.std import qt_tqdm

from qtpy.QtCore import QThread, SignalInstance, Signal
from qtpy import QtWidgets


class ABThread(QThread):
    status: SignalInstance = Signal(int, str)
    exception: SignalInstance = Signal(Exception)

    _args = ()
    _kwargs = {}

    def __init__(self, parent=None):
        super().__init__(parent)

        from activity_browser import application
        self.exception.connect(application.main_window.dialog_on_exception)

    def start(self, *args, priority=QThread.NormalPriority, **kwargs):
        """
        Reimplemented from QThread to set the priority of the thread.
        """
        self._args = args
        self._kwargs = kwargs
        super().start(priority)

    def run(self):
        """Reimplemented from QThread to close any database connections before finishing."""
        qt_tqdm.updated.connect(self._emit_status)

        # call run_safely and finish by closing the connections
        with SafeBWConnection(), InfoToSlot(self.status.emit):
            try:
                self.run_safely(*self._args, **self._kwargs)
            except Exception as e:
                # send exception signal
                self.exception.emit(e)
                raise e

        qt_tqdm.updated.disconnect(self._emit_status)
        self.status.emit(100, "Complete")

    def _emit_status(self, progress: int, message: str):
        if progress == 100:
            self.status.emit(-1, "Working...")
        else:
            self.status.emit(progress, message)

    def run_safely(self, *args, **kwargs):
        raise NotImplementedError

    def connect_progress_dialog(self, progress_dialog: QtWidgets.QProgressDialog):
        """
        Connects the status signal to a progress dialog.
        """
        def slot(progress, message):
            if progress == -1:
                progress_dialog.setLabelText(message)
                progress_dialog.setRange(0, 0)
            else:
                progress_dialog.setRange(0, 100)
                progress_dialog.setValue(progress)
                progress_dialog.setLabelText(message or "Working...")

        self.status.connect(slot)


class SafeBWConnection:
    def __enter__(self):
        return

    def __exit__(self, *args):
        """
        Closes all connections for this thread
        """
        for conn in getattr(thread_local, "peewee_connections", []):
            if hasattr(conn, "conn") and hasattr(conn.conn, "close"):
                conn.conn.close()


class InfoToSlot:
    def __init__(self, progress_slot=lambda progress, message: None):
        self.handler = LoggingProgressHandler("INFO")
        thread_local.progress_slot = progress_slot

    def __enter__(self):
        logging.root.addHandler(self.handler)
        return

    def __exit__(self, *args):
        logging.root.removeHandler(self.handler)
        return


class LoggingProgressHandler(logging.Handler):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.thread != threading.get_ident():
            return False
        if record.levelname != "INFO":
            return False
        return True

    def emit(self, record: logging.LogRecord):
        try:
            thread_local.progress_slot(None, record.message)
        except AttributeError:
            pass


thread_local = threading.local()
