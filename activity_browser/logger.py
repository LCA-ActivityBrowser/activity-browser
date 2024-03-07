import os
import sys
import time
import inspect
import logging
import threading
import appdirs

from traceback import extract_tb
from io import StringIO
from types import TracebackType
from typing import TextIO, Type


class LowLevelStdIO:
    """
    This class will replace the filehandles of the supplied StdIO with own ones so changes to said stream can be caught.
    It will instantiate a capturing thread that will read lines from the stream and log them using a logger called
    "C/C++". The original StdIO filehandle is preserved so we can still write to it using the "write" method.
    """
    def __init__(self, stdio: TextIO):
        # Save a copy of the true StdIO
        self.fileno = stdio.fileno()
        self.true_stdio = os.dup(self.fileno)

        # create a pipe and place the inlet on top of the StdIO using os.dup2
        self.pipe_out, self.pipe_in = os.pipe()
        os.dup2(self.pipe_in, self.fileno)
        os.close(self.pipe_in)

        # initiate a thread with capture as target, and as daemon so it closes when ab closes
        self.thread = threading.Thread(target=self.capture, daemon=True)

        # initiate a logger with "C/C++" as name
        self.logger = custom_logger("C/C++")

    def capture(self):
        # open the output of the pipe as a line-file
        readfile = os.fdopen(self.pipe_out)
        while True:
            # read the next line, or block until there is one
            data = readfile.readline()

            # log the line as PRINT
            self.logger.log(25, data)

    def start_capture(self, thread_name=None):
        # create a thread with the name for recognition, start the thread
        self.thread.setName(thread_name)
        self.thread.start()

        # return self for easy chaining during instantiation
        return self

    def write(self, line: str):
        # access the original stdio and write a line to it
        os.write(self.true_stdio, line.encode())


class HighLevelStdIO(StringIO):
    """
    This subclass of StringIO may be used to replace the normal sys.stdout and sys.stderr streams. If anything is
    written to them by a python module it is caught here and put in our logging workflow which will eventually write
    them directly to the LowLevelStdIO.

    Benefit of catching them here instead of all at the LowLevelStdIO is that we can access the context of the call and
    create appropriate logger calls.
    """

    filters = [
        "pyprind"
    ]

    def write(self, string: str):
        """Capture write calls made to this StdIO"""
        # get the modulename from the context
        module = get_module(height=2)

        # apply the (very simple) filter
        for name in self.filters:
            if name in module: return

        # get a custom logger using the module name and log as PRINT
        logger = custom_logger(module)
        logger.log(25, string)


class ABConsoleHandler(logging.Handler):
    """
    LogHandler for the console. Make sure they are all in the same format. Adds badges, and if extended logs are enabled
    also the time and a (shortened) logger name.
    """
    badge = {
        "INFO": "\u001b[48;5;24m INFO  \u001b[0m",
        "DEBUG": "\u001b[48;5;90m DEBUG \u001b[0m",
        "EXCEPTION": "\u001b[48;5;88m EXCPT \u001b[0m",
        "ERROR": "\u001b[48;5;88m ERROR \u001b[0m",
        "WARNING": "\u001b[48;5;130m WARN  \u001b[0m",
        "PRINT": "\u001b[7m PRINT \u001b[0m",
    }

    alias = {
        "activity_browser": "AB",
        "brightway2": "BW2"
    }

    extended_debug = os.environ.get("EXTEND_DEBUG", False)

    def handle(self, record: logging.LogRecord):
        """Handle a new LogRecord"""
        message = self.format_log(record)
        low_level_stdout.write(message)

        if record.exc_info:
            exc_message = self.format_exception(record.exc_info[2])
            low_level_stdout.write(exc_message)

    def format_log(self, record: logging.LogRecord) -> str:
        """Format a LogRecord"""
        # format message to a single line
        message = " ".join(record.msg.split("\n"))
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

        # that's all we need for a regular console
        if not self.extended_debug: return f"{badge} {message}\n"

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
        space = 7
        if self.extended_debug:
            space = 37

        traceback = extract_tb(traceback)
        message = "\u001b[38;5;1m\u001b[1m"
        for frame in traceback:
            line1 = f'{space * " "}File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
            line2 = f"{space * ' '} {frame.line}\n"
            message = message + line1 + line2
        message = f"{message}\u001b[0m"
        return message


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

        # create the logfile and write the headers
        with open(self.filepath, 'a') as log_file:
            log_file.write(";".join(self.headers) + "\n")

    def handle(self, record: logging.LogRecord):
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
        message = " ".join(record.msg.split("\n"))
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

    def exception(self, msg, *args):
        self.log(40, msg, *args)

    def log(self, level: int, msg, *args):
        """
        Get all logrecord info ourselves by inspecting the stack and log it by requesting a logger with the __name__ of
        the module from which the proxy was called.

        Do not use directly: it will inspect a frame too high in that case.
        """
        # get frame info from 2 frames up in the stack, retrieve the name of the module
        frame_info = inspect.stack()[2]
        name = inspect.getmodule(frame_info.frame).__name__

        # create a LogRecord using all the supplied information
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname=frame_info.filename,
            lineno=frame_info.lineno,
            msg=msg,
            args=args,
            exc_info=None,
            func=frame_info.function
        )

        # get the logger with the module's name and let it handle the record
        logger = logging.getLogger(name)
        logger.handle(record)


def get_module(height: int = 0) -> str:
    """Finds module based on the current callstack and returns the name as string"""
    frame_info = inspect.stack()[height]
    return inspect.getmodule(frame_info.frame).__name__


def exception_hook(error: Type[BaseException], message: BaseException, traceback: TracebackType):
    """Exception hook to catch and log exceptions"""
    source = get_module(2)
    logger = custom_logger(source)

    exc_info = (error, message, traceback)
    logger.exception(f"{error.__name__}: {message}", exc_info=exc_info)


def custom_logger(name: str):
    """
    Create a logger with the given name and hooks it into the AB handlers. Propagation is disabled to make sure there is
    no duplicate logging if this function is called multiple times.
    """
    logger = logging.getLogger(name)
    logger.setLevel("DEBUG")
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def root_logger():
    ab_logger = logging.getLogger("activity_browser")
    ab_logger.setLevel("DEBUG")
    ab_logger.addHandler(console_handler)
    ab_logger.addHandler(file_handler)
    return ab_logger


# add our own level name for printed logs
logging.addLevelName(25, "PRINT")

# setting up our own logger
console_handler = ABConsoleHandler()
file_handler = ABFileHandler()
root_logger()

# replace the low and high level StdIO's
low_level_stdout = LowLevelStdIO(sys.stdout).start_capture("StdoutCapture")
low_level_stderr = LowLevelStdIO(sys.stderr).start_capture("StderrCapture")

sys.stdout = HighLevelStdIO()
sys.stderr = HighLevelStdIO()

log = LoggingProxy()
