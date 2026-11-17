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

    for name, no, color in (
        ("SYNC", 9, "<cyan>"),
        ("SIGNAL", 19, "<yellow>"),
        ("TEST", 19, "<cyan>"),
    ):
        try:
            logger.level(name, no=no, color=color)
        except ValueError:
            # Already registered (e.g. setup_logging called more than once).
            pass

    logger.remove()
    # Windowed PyInstaller builds (console=False) set sys.stderr to None on Windows.
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level=6,
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        )

    log_dir = platformdirs.user_log_dir(appname="ActivityBrowser", appauthor="pylca")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "activity_browser.log")
    logger.add(log_file, level="DEBUG", rotation="5 MB", retention=5)

def run_activity_browser():
    from . import __main__ as ab_main

    ab_main.run_activity_browser()

setup_logging()