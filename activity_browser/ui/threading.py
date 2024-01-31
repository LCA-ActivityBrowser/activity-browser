from PySide2.QtCore import QThread
import brightway2 as bw


class ABThread(QThread):

    def exit(self, retcode: int = ...) -> None:
        # cleaning up the DB connections in this thread
        for _, SubstitutableDatabase in bw.config.sqlite3_databases:
            if not SubstitutableDatabase.db.is_closed():
                SubstitutableDatabase.db.close()
        return super().exit(retcode)
