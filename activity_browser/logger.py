import logging
import os
import time
import appdirs

from .signals import signals


class ABHandler(object):
    """
    Creates two logging streams, one to the console (with >=INFORMATION logs)
    the second to a file specified with the name argument (with >=DEBUG logs)
    and attaches these to a logger created in the calling modules.

    There are 4 available levels in AB, increasing in importance:
    - DEBUG
    - INFO
    - WARNING
    - ERROR
    - CRITICAL is available in logging but not implemented in AB
    See also: https://docs.python.org/3/library/logging.html#levels

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
        ABHandler.file_path = os.path.join(dir_path, name)
        ABHandler.stream_handler = logging.StreamHandler()
        ABHandler.file_handler = logging.FileHandler(ABHandler.file_path)

        log_format = logging.Formatter("%(asctime)s-%(levelname)s - %(ABmodule)s: %(message)s")

        console_format = logging.Formatter("%(message)s")
        ABHandler.stream_handler.setFormatter(console_format)
        ABHandler.file_handler.setFormatter(log_format)

        ABHandler.stream_handler.setLevel(logging.INFO)
        ABHandler.file_handler.setLevel(logging.DEBUG)

        ABHandler.qt_handler = ABLogHandler()
        ABHandler.qt_handler.setFormatter(console_format)

        return ABHandler.setup_with_logger(logger)

    @classmethod
    def setup_with_logger(cls, logger: logging.Logger = None, module: str = None) -> object:
        """
        Links the logger object to the different stream handlers. This avoids the process of
        creating new handlers and should be the general method to call for linking the
        logging.Logger objects.

        Parameters
        ----------
        logger: an object of type logging.Logger requiring setup with logging.Handlers
        module: name of the logging module

        Returns
        -------
        ABHandler: the logging handler

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
    def timestamp() -> str:
        """Return a timestamped string, the format provided is:
        day of the year _ month _ day - hour _ minute _ second"""
        stmp = time.localtime()
        return f"-{stmp.tm_year}-{stmp.tm_mon}-{stmp.tm_mday}_{stmp.tm_hour}-{stmp.tm_min}-{stmp.tm_sec}"

    @staticmethod
    def clean_directory(dirpath: str) -> None:
        """Clean the Activity-Browser/log directory of all files older than 365 days"""
        time_limit = time.time() - 24*3600*365
        for file in os.listdir(dirpath):
            filepath = os.path.join(dirpath, file)
            if os.stat(filepath).st_mtime < time_limit:
                os.remove(filepath)

    def log_file_path(self) -> str:
        return ABHandler.file_path

    def message(self, *args) -> str:
        str_ = ''
        for arg in args:
            if not isinstance(arg, str):
                str_ += str(arg)
            else:
                str_ += arg
        return str_

    def debug(self, msg: str, *args) -> None:
        ABHandler.log.debug(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def info(self, msg: str, *args) -> None:
        ABHandler.log.info(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def warning(self, msg: str, *args) -> None:
        ABHandler.log.warning(self.message(msg, *args), extra={'ABmodule': self.module_name})

    def error(self, msg: str = None, *args, **kwargs) -> None:
        """Provides a wrapper for the Logger.error method. This is to keep the logging messages
        consistent with previous practices. Exception handling is provided through the use of
        kwargs

        Parameters
        ----------
        msg, *args: strings that form the logging message, multiple strings allowed
        **kwargs: provided for the handling of stack traces, the two arguments taken here are:
                error=''
                exc_info=bool

        Returns
        -------

        """
        if msg is not None:
            ABHandler.log.error(self.message(msg, *args), extra={'ABmodule': self.module_name})

        exc_info = True  # TODO Move this error handling with the use of kwargs into a single error message
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
