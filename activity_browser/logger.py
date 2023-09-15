from PySide2.QtCore import Slot
import logging
import os, time, appdirs
import random, string

from .signals import signals


class ABHandler(object):
    """
    Creates two logging streams, one to the console (with >=INFORMATION logs)
    the second to a file specified with the name argument (with >=WARNING logs)
    and attaches these to a logger created in the calling modules.

    Provides the formats and initialization procedures for the logging streams.
    """
    log = None
    file_path = None
    stream_handler = None
    file_handler = None
    qt_handler = None

    def __init__(self, name: str = None):
        self.module_name = name

    @staticmethod
    def initialize_with_logger(logger: logging.Logger):
        """
        Will initialize the handlers for the logging streams and check that the file handler
        is properly setup before linking to the passed Logger object.

        Parameters
        ----------
        logger: an object of type logging.Logger obtained in the calling module with getLogger()
        """
        name = logger.name + ABHandler.timestamp() + '.log'
        dir_path = appdirs.user_log_dir('ActivityBrowser', 'ActivityBrowser')
        os.makedirs(dir_path, exist_ok=True)
        ABHandler.clean_directory(dir_path)
        ABHandler.file_path = dir_path + "/" + name
        ABHandler.stream_handler = logging.StreamHandler()
        ABHandler.file_handler = logging.FileHandler(ABHandler.file_path)

        log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(ABmodule)s - %(message)s - ")

        console_format = logging.Formatter("%(message)s")
        ABHandler.stream_handler.setFormatter(console_format)
        ABHandler.file_handler.setFormatter(log_format)

        ABHandler.stream_handler.setLevel(logging.INFO)
        ABHandler.file_handler.setLevel(logging.DEBUG)

        ABHandler.qt_handler = ABLogHandler()
        ABHandler.qt_handler.setFormatter(console_format)

        return ABHandler.setup_with_logger(logger)

    @classmethod
    def setup_with_logger(cls, logger: logging.Logger = None, module: str = None):
        """
        Links the logger object to the different stream handlers. This avoids the process of
        creating new handlers and should be the general method to call for linking the
        logging.Logger objects.

        Parameters
        ----------
        logger: an object of type logging.Logger requiring setup with logging.Handlers
        """

        ABHandler.log = logger
        assert ABHandler.log is not None

        ABHandler.log.addHandler(ABHandler.stream_handler)
        ABHandler.log.addHandler(ABHandler.file_handler)
        ABHandler.log.addHandler(ABHandler.qt_handler)
        ABHandler.log.setLevel(logging.INFO)

        if module is not None:
            return ABHandler(module)
        return ABHandler("root")

    @staticmethod
    def unique_string(n: int) -> str:
        """Returns a random string of length n, to avoid issues with non-unique log files"""
        return ''.join(random.choice(string.ascii_letters) for i in range(n))

    @staticmethod
    def timestamp() -> str:
        """Returns a timestamped string, the format provided is:
        day of the month _ month _ year - hour _ minute _ second"""
        stmp = time.localtime()
        return f"-{stmp.tm_mday}_{stmp.tm_mon}_{stmp.tm_year}-{stmp.tm_hour}_{stmp.tm_min}_{stmp.tm_sec}"

    @staticmethod
    def clean_directory(dirpath: str) -> None:
        """Cleans the Activity-Browser/log directory of all files older than 365 days"""
        time_limit = time.time() - 24*3600*365
        for file in os.listdir(dirpath):
            filepath = dirpath + '/' + file
            if os.stat(filepath).st_mtime < time_limit:
                os.remove(filepath)

    def log_file_path(self):
        return ABHandler.file_path

    def message(self, *args) -> str:
        _str = ''
        for arg in args:
            if not isinstance(arg, str):
                _str += str(arg)
            else:
                _str += arg
        return _str

    def debug(self, msg: str, *args) -> None:
        ABHandler.log.debug(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def info(self, msg: str, *args) -> None:
        ABHandler.log.info(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def warning(self, msg: str, *args) -> None:
        ABHandler.log.warning(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def error(self, msg: str = None, *args, **kwargs) -> None:
        """ Provides a wrapper for the Logger.error method. This is to keep the logging messages
        consistent with previous practices. Exception handling is provided through the use of
        kwargs
        Parameters:
            msg, *args: strings that form the logging message, multiple strings allowed
            **kwargs: provided for the handling of stack traces, the two arguments taken here are:
                error=''
                exc_info=bool
        """
        if msg is not None:
            ABHandler.log.error(self.message(msg, *args), extra={'ABmodule': self.module_name})

        exc_info = True # TODO Move this error handling with the use of kwargs into a single error message
        if kwargs and 'error' in kwargs:
            if 'exc_info' in kwargs:
                exc_info = kwargs['exc_info']
            ABHandler.log.error(kwargs['error'], exc_info=exc_info)

    def addHandler(self, handler) -> None:
        ABHandler.log.addHandler(handler)

    def setLevel(self, level, root: bool = False) -> None:
        if root:
            ABHandler.log.root.setLevel(level)
        else:
            ABHandler.log.setLevel(level)


class ABLogHandler(logging.Handler):
    """Customizing a handler for running within a separate thread, emitting logs to the main
    thread."""
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)

    def emit(self, record):
        msg = self.format(record)
        signals.log.emit(msg)


logger = logging.getLogger('ab_logs')
log = ABHandler.initialize_with_logger(logger)

#handler = ABLogHandler()
#handler.setFormatter(logging.Formatter("%(module)s - %(levelname)s - %(asctime)s - %(message)s"))
#log = ABHandler('ab_logs')
#log.addHandler(handler)
#log.propagate = True
#logging.setLoggerClass(ABHandler)
