# -*- coding: utf-8 -*-
import sys
from logging import getLogger

try:
    import PySide6
except ImportError:
    import qtpy

from .logger import log_file_location, setup_ab_logging
from .mod import bw2data
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .info import __version__ as version
from .layouts.main import MainWindow
from .plugin import Plugin
from .controllers import *

log = getLogger(__name__)


def load_settings() -> None:
    if ab_settings.settings:
        bw2data.projects.switch_dir(ab_settings.current_bw_dir)
        bw2data.projects.set_current(ab_settings.startup_project)
    log.info(f"Brightway2 data directory: {bw2data.projects.base_dir}")
    log.info(f"Brightway2 current project: {bw2data.projects.current}")


def run_activity_browser():
    setup_ab_logging()
    log.info(f"Activity Browser version: {version}")
    if log_file_location:
        log.info(f"The log file can be found at {log_file_location}")

    application.main_window = MainWindow(application)
    load_settings()
    application.show()

    sys.exit(application.exec_())
