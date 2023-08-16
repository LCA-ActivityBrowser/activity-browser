from PySide2.QtCore import Slot
import logging
import os, time
import random, string


from .signals import signals
class Logger(logging.Logger):
    """
    Creates two logging streams, one to the console (with >=INFORMATION logs)
    the second to a file specified with the name argument (with >=WARNING logs)
    and attaches these to a logger.

    Returns the logging device
    """
    file_handler = None
    def __init__(self, name: str):
        super().__init__(name)
        self.setLevel(logging.INFO)

        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setLevel(logging.INFO)
        # Threads have their own Logger, but these refer to the sessions log file
        if Logger.file_handler is None:
            dir_path = os.getcwd() + "/.logs"
            os.makedirs(dir_path, exist_ok=True)
            Logger.cleanDirectory(dir_path)
            name = name + "_" + Logger.uniqueString(8) + '.log'
            file_path = dir_path + "/" + name
            Logger.file_handler = logging.FileHandler(file_path)
        Logger.file_handler.setLevel(logging.WARNING)

        self.log_format = logging.Formatter("%(module)s - %(levelname)s - %(asctime)s - %(message)s")
        self.stream_handler.setFormatter(self.log_format)
        Logger.file_handler.setFormatter(self.log_format)

        self.addHandler(self.stream_handler)
        self.addHandler(Logger.file_handler)

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

    @classmethod
    def getLogger(cls, name: str = None):
        assert name is not None
        return cls(name)

    def message(self, *args):
        _str = ''
        for arg in args:
            if not isinstance(arg, str):
                _str += str(arg)
            else:
                _str += arg
        return _str

    def info(self, msg , *args):
        if args:
            msg = self.message(msg, *args)
        super().info(msg)

    def warning(self, msg, *args):
        if args:
            msg = self.message(msg, *args)
        super().warning(msg)

    def error(self, msg, *args):
        if args:
            msg = self.message(msg, *args)
        super().error(msg)


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
log = Logger('ab_logs')
log.addHandler(handler)