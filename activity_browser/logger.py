import os
import sys
import time
import inspect
import logging
import appdirs

from traceback import extract_tb
from types import TracebackType
from typing import Type


class ABFileHandler(logging.Handler):
    """
    LogHandler for the log files. Formats them in semicolon separated CSV files for easy reading.
    """
    headers = ["time", "type", "thread", "name", "file location", "line number", "function name", "message"]

    def __init__(self):
        super().__init__()

        # create a unique filename based on the datetime
        self.filename = "ab_logs" + self.timestamp() + '.csv'

        # set dir and create it if it doesn't exist yet
        dir_path = appdirs.user_log_dir('ActivityBrowser', 'ActivityBrowser')
        os.makedirs(dir_path, exist_ok=True)

        # create final filepath of the logfile of this session
        self.filepath = os.path.join(dir_path, self.filename)

        # set the global file location
        global log_file_location
        log_file_location = self.filepath

        # create the logfile and write the headers
        with open(self.filepath, 'a') as log_file:
            log_file.write(";".join(self.headers) + "\n")

    def emit(self, record: logging.LogRecord):
        """Handle a new LogRecord"""
        # format the message from the record
        message = self.format(record)

        # append to the logfile
        with open(self.filepath, 'a') as log_file:
            log_file.write(message)

            # if there's exception info, write the exception traceback to the file as well
            if record.exc_info:
                exc_message = self.format_exception(record.exc_info[2])
                log_file.write(exc_message)

    def format(self, record: logging.LogRecord) -> str:
        """Format a LogRecord"""
        # format message to a single line
        message = " ".join(str(record.msg).split("\n"))
        message = message + " ".join([str(arg) for arg in record.args])

        # if there is no message left, return nothing
        if message == " ": return ""

        # make sure there a no semicolons
        message.replace(';', ':')

        # convert time
        struct_time = time.localtime(record.created)
        readable_time = time.strftime("%H:%M.%S", struct_time)

        line = f"{readable_time};{record.levelname};{record.threadName};{record.name};{record.pathname};{record.lineno};{record.funcName};{message}"
        return f"{line}\n"

    def format_exception(self, traceback: TracebackType) -> str:
        """Format the traceback of an exception"""
        # extract the traceback
        traceback = extract_tb(traceback)
        message = ""

        # append a line for each frame in the traceback
        for frame in traceback:
            line = f";TRACEBACK;;;{frame.filename};{frame.lineno};{frame.name};{frame.line}"
            message = f"{message}{line}\n"

        # return the string containing multiple lines
        return message

    def timestamp(self) -> str:
        """Return a timestamped string, the format provided is:
        day of the year _ month _ day - hour _ minute _ second"""
        stmp = time.localtime()
        return f"-{stmp.tm_year}-{stmp.tm_mon}-{stmp.tm_mday}_{stmp.tm_hour}-{stmp.tm_min}-{stmp.tm_sec}"


class ABPycharmHandler(logging.Handler):
    """
    LogHandler for the console. Make sure they are all in the same format. Adds badges, and if extended logs are enabled
    also the time and a (shortened) logger name.
    """
    badge = {
        "INFO": "\u001b[48;5;24m\u001b[38;5;255m INFO  \u001b[0m",
        "DEBUG": "\u001b[48;5;90m\u001b[38;5;255m DEBUG \u001b[0m",
        "EXCEPTION": "\u001b[48;5;88m\u001b[38;5;255m EXCPT \u001b[0m",
        "ERROR": "\u001b[48;5;88m\u001b[38;5;255m ERROR \u001b[0m",
        "WARNING": "\u001b[48;5;130m\u001b[38;5;255m WARN  \u001b[0m",
        "PRINT": "\u001b[7m PRINT \u001b[0m",
    }

    alias = {
        "activity_browser": "AB",
        "brightway2": "BW2"
    }

    def __init__(self):
        super().__init__()
        # create a unique filename based on the datetime
        self.filename = "pycharm_logs.log"

        # set dir and create it if it doesn't exist yet
        dir_path = appdirs.user_log_dir('ActivityBrowser', 'ActivityBrowser')
        os.makedirs(dir_path, exist_ok=True)

        # create final filepath of the logfile of this session
        self.filepath = os.path.join(dir_path, self.filename)

    def emit(self, record: logging.LogRecord):
        """Handle a new LogRecord"""
        # format message
        message = self.format_log(record)

        # append to the logfile
        with open(self.filepath, 'a') as log_file:
            log_file.write(message)

            # if there's exception info, write the exception traceback to the file as well
            if record.exc_info:
                exc_message = self.format_exception(record.exc_info[2])
                log_file.write(exc_message)

    def format_log(self, record: logging.LogRecord) -> str:
        """Format a LogRecord"""
        # format message to a single line
        message = " ".join(str(record.msg).split("\n"))
        message = message + " ".join([str(arg) for arg in record.args])

        # if there is no message left, return nothing
        if message == " ": return ""

        # clean-up if the message is a C++ error message
        if message.startswith('[') and message.index(':') < message.index(']'):
            # most likely a c++ error log, otherwise, very bad luck
            i = message.index(']') + 2
            message = message[i:]

        # retrieve the badge
        badge = self.badge[record.levelname]
        if record.exc_info:
            badge = self.badge["EXCEPTION"]

        # get a clean timestamp
        time_stamp = time.asctime()[11:19]

        source_str = self.format_source(record.name)

        return f"{time_stamp} {source_str}{badge} {message}\n"

    def format_source(self, name: str) -> str:
        """
        The entire source may be too long for the console window. Here we replace known sources with their alias, only
        use the first two modules and cut it short if it's still too long
        """
        # create list of the module string
        module_split = name.split('.')

        # switch a possible alias
        for key, alias in self.alias.items():
            if key == module_split[0]:
                module_split[0] = alias

        # rebuild only the first two modules
        source_str = ".".join(module_split[:2])

        # adjust length
        if len(source_str) >= 20:
            source_str = source_str[:16] + "..."

        return source_str.ljust(20)

    def format_exception(self, traceback: TracebackType) -> str:
        """Format the traceback of an exception"""
        space = 37

        traceback = extract_tb(traceback)
        message = "\u001b[38;5;1m\u001b[1m"
        for frame in traceback:
            line1 = f'{space * " "}File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
            line2 = f"{space * ' '} {frame.line}\n"
            message = message + line1 + line2
        message = f"{message}\u001b[0m"
        return message


class LoggingProxy:
    """
    Official logging documentation states that loggers should be initiated per module using the __name__ attribute of
    said module. Doing this for each module is in my opinion messy and unneeded. Enter: this proxy that modules can use
    by importing log from the activity_browser module. By logging via this proxy the loggers are initiated dynamically
    through inspecting the frame in which the proxy was called.
    """
    def debug(self, msg, *args):
        self.log(10, msg, *args)

    def info(self, msg, *args):
        self.log(20, msg, *args)

    def warning(self, msg, *args):
        self.log(30, msg, *args)

    def warn(self, msg, *args):
        self.log(30, msg, *args)

    def error(self, msg, *args):
        self.log(40, msg, *args)

    def exception(self, msg, *args, exc_info):
        self.log(40, msg, *args, stack_level=3, exc_info=exc_info)

    def print(self, msg):
        self.log(25, msg,  stack_level=3)

    def log(self, level: int, msg, *args, stack_level: int = 2, exc_info: tuple = None):
        """
        Get all logrecord info ourselves by inspecting the stack and log it by requesting a logger with the __name__ of
        the module from which the proxy was called.

        Do not use directly: it will inspect a frame too high in that case.
        """
        # get frame info from 2 frames up in the stack, retrieve the name of the module
        frame_info = inspect.stack()[stack_level]
        name = inspect.getmodule(frame_info.frame).__name__

        # already solve args
        msg = msg + " ".join([str(arg) for arg in args])

        # create a LogRecord using all the supplied information
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname=frame_info.filename,
            lineno=frame_info.lineno,
            msg=msg,
            args=tuple(),
            exc_info=exc_info,
            func=frame_info.function
        )

        # get the logger with the module's name and let it handle the record
        logger = logging.getLogger(name)
        logger.handle(record)


def exception_hook(error: Type[BaseException], message: BaseException, traceback: TracebackType):
    """Exception hook to catch and log exceptions"""
    exc_info = (error, message, traceback)
    log.exception(f"{error.__name__}: {message}", exc_info=exc_info)


def setup():
    # set the root logger's level to 0, this gives us access to all logs
    logging.root.setLevel(0)

    # peewee is mad, so set to info
    logging.getLogger("peewee").setLevel("INFO")

    # setting up a basic stderr handler
    stderr_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%H:%M:%S')
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel("INFO")
    logging.root.addHandler(stderr_handler)

    # setting up the pycharm handler
    pycharm_handler = ABPycharmHandler()
    logging.root.addHandler(pycharm_handler)

    # setting up the file handler
    file_handler = ABFileHandler()
    logging.root.addHandler(file_handler)

    # setting up the exception hook
    sys.excepthook = exception_hook


setup()

log = LoggingProxy()
log_file_location = None
