import sys

from PySide2.QtCore import QThread
from activity_browser.mod import bw2data as bd
from activity_browser.logger import exception_hook


class ABThread(QThread):

    def run(self):
        """Reimplemented from QThread to close any database connections before finishing."""
        # call run_safely and finish by closing the connections
        try:
            self.run_safely()
            self.close_connections()
        # also close the connections if any exception occurs
        except Exception as e:
            self.close_connections()
            raise e

    def close_connections(self):
        """
        Closes all connections for this thread
        """
        for _, SubstitutableDatabase in bd.config.sqlite3_databases:
            if not SubstitutableDatabase.db.is_closed():
                SubstitutableDatabase.db.close()

    def run_safely(self):
        raise NotImplementedError
