from PySide2.QtCore import Slot
import logging
import os, time
import random, string


from .signals import signals
class ABLogger(object):
    """
    Creates two logging streams, one to the console (with >=INFORMATION logs)
    the second to a file specified with the name argument (with >=WARNING logs)
    and attaches these to a logger.

    Returns the logging device
    """
    file_handler = None
    def __init__(self, name: str): # TODO use the logging.getABLogger() method
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        dir_path = os.getcwd() + "/.logs"
        os.makedirs(dir_path, exist_ok=True)
        ABLogger.cleanDirectory(dir_path)
        name = name + "_" + ABLogger.uniqueString(8) + '.log'
        file_path = dir_path + "/" + name
        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setLevel(logging.INFO)
        ABLogger.file_handler = logging.FileHandler(file_path)
        ABLogger.file_handler.setLevel(logging.WARNING)

        self.log_format = logging.Formatter("%(module)s - %(levelname)s - %(asctime)s - %(message)s")
        self.stream_handler.setFormatter(self.log_format)
        ABLogger.file_handler.setFormatter(self.log_format)

        self.logger.addHandler(self.stream_handler)
        self.logger.addHandler(ABLogger.file_handler)

    @staticmethod
    def uniqueString(n: int) -> str:
        """Returns a random string of length n, to avoid issues with non-unique log files"""
        return ''.join(random.choice(string.ascii_letters) for i in range(n))

    @staticmethod
    def cleanDirectory(dirpath: str) -> None:
        time_limit = time.time() - 24*3600*7
        for file in os.listdir(dirpath):
            filepath = dirpath + '/' + file
            if os.stat(filepath).st_mtime < time_limit:
                os.remove(filepath)

    def message(self, *args) -> str:
        _str = ''
        for arg in args:
            if not isinstance(arg, str):
                _str += str(arg)
            else:
                _str += arg
        return _str

    def info(self, msg , *args) -> None:
        if args:
            msg = self.message(msg, *args)
        self.logger.info(msg)

    def warning(self, msg, *args) -> None:
        if args:
            msg = self.message(msg, *args)
        self.logger.warning(msg)

    def error(self, msg, *args) -> None:
        if args:
            msg = self.message(msg, *args)
        self.logger.error(msg)

    def addHandler(self, handler) -> None:
        self.logger.addHandler(handler)

    def propagate(self, true: bool) -> None:
        self.logger.propagate = true

    def setLevel(self, level, root: bool = False) -> None:
        if root:
            self.logger.root.setLevel(level)
        else:
            self.logger.setLevel(level)


class ABLogHandler(logging.Handler):
    """Customizing a handler for running within a separate thread, emitting logs to the main
    thread."""
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)

    def emit(self, record):
        msg = self.format(record)
        signals.log.emit(msg)


handler = ABLogHandler()
handler.setFormatter(logging.Formatter("%(module)s - %(levelname)s - %(asctime)s - %(message)s"))
log = ABLogger('ab_logs')
log.addHandler(handler)
log.addHandler(logging.NullHandler())
log.propagate(True)
