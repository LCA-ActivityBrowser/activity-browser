from PySide2.QtCore import QThread
import brightway2 as bw


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
        todo: move to an appropriate controller
        """
        for _, SubstitutableDatabase in bw.config.sqlite3_databases:
            if not SubstitutableDatabase.db.is_closed():
                SubstitutableDatabase.db.close()

    def run_safely(self):
        raise NotImplementedError
