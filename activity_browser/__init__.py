# -*- coding: utf-8 -*-
import sys
import traceback

from activity_browser.brightway import bw2data
from .logger import log
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .controllers import *
from .info import __version__ as version
from .layouts.main import MainWindow
from .plugin import Plugin


def load_settings() -> None:
    if ab_settings.settings:
        log.info("Loading user settings:")
        bw2data.projects.switch_dir(ab_settings.current_bw_dir)
        bw2data.projects.set_current(ab_settings.startup_project)
    log.info(f'Brightway2 data directory: {bw2data.projects.base_dir}')
    log.info(f'Brightway2 active project: {bw2data.projects.current}')


def run_activity_browser():
    log.info(f'The Activity Browser log file can be found at {log.log_file_path()}')
    log.info(f'Activity Browser version: {version}')

    application.main_window = MainWindow(application)
    load_settings()
    application.show()

    def exception_hook(*args):
        log.warning(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(application.exec_())
