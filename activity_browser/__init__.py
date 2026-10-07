import sys

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