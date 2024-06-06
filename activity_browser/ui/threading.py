import sys
import threading
import logging

from activity_browser.mod import bw2data as bd
from activity_browser.logger import exception_hook

from PySide2.QtCore import QThread, SignalInstance, Signal


class ABThread(QThread):
    status: SignalInstance = Signal(int, str)

    def run(self):
        """Reimplemented from QThread to close any database connections before finishing."""
        # call run_safely and finish by closing the connections
        with SafeBWConnection(), InfoToSlot(self.status.emit):
            try:
                self.run_safely()
            except Exception as e:
                # pass exception to our excepthook
                exception_hook(*sys.exc_info())
                raise e

    def run_safely(self):
        raise NotImplementedError


class SafeBWConnection:

    def __enter__(self):
        return

    def __exit__(self, *args):
        """
        Closes all connections for this thread
        """
        for _, SubstitutableDatabase in bd.config.sqlite3_databases:
            if not SubstitutableDatabase.db.is_closed():
                SubstitutableDatabase.db.close()


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
        if record.thread != threading.get_ident(): return False
        if record.levelname != "INFO": return False
        return True

    def emit(self, record: logging.LogRecord):
        try:
            thread_local.progress_slot(None, record.message)
        except AttributeError:
            pass


thread_local = threading.local()
