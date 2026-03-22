import sys

# This patch fixes a bug on Python 3.10 where shiboken6 patches the typing module with a broken Self type. Only way to
# fix it is to patch it ourselves first.
if sys.version_info[1] < 11:
    import typing
    if hasattr(typing, "Self"): # if Self has already been patched into typing, delete it first
        del typing.Self
    import typing_extensions
    setattr(typing, "Self", typing_extensions.Self)

try:
    import PySide6
except ImportError:
    import qtpy

def setup_logging():
    """Configure loguru sinks for console and file logging."""
    from loguru import logger
    import os
    import platformdirs

    logger.level("SYNC", no=9, color="<cyan>")
    logger.level("SIGNAL", no=19, color="<yellow>")
    logger.level("TEST", no=19, color="<cyan>")

    logger.remove()
    logger.add(sys.stderr, level=6, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

    log_dir = platformdirs.user_log_dir(appname="ActivityBrowser", appauthor="pylca")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "activity_browser.log")
    logger.add(log_file, level="DEBUG", rotation="5 MB", retention=5)

def run_activity_browser():
    from .__main__ import run_activity_browser

setup_logging()