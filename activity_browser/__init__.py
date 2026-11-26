import os
import sys

# Prefer PySide6 when multiple Qt bindings are installed (conda/pip mixes).
os.environ.setdefault("QT_API", "pyside6")

try:
    import PySide6  # noqa: F401
except ImportError:
    import qtpy  # noqa: F401
else:
    # Must run after PySide6 so shiboken's feature hook is registered.
    from .shiboken_compat import patch_shiboken_feature_hook

    patch_shiboken_feature_hook()


def setup_logging():
    """Configure loguru sinks for console and file logging."""
    from loguru import logger
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
    # Windows frozen builds (PyInstaller): Pool/Process workers re-enter the
    # app entry. Divert them before the GUI starts even if the wrapper script
    # forgot freeze_support (see run-activity-browser.py).
    import multiprocessing

    multiprocessing.freeze_support()
    from . import __main__ as ab_main

    ab_main.run_activity_browser()


setup_logging()
