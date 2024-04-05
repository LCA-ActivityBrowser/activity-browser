# -*- coding: utf-8 -*-
import sys
import traceback

from .logger import log
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .controllers import *
from .info import __version__ as version
from .layouts.main import MainWindow
from .plugin import Plugin


def controller_logger():
    database_controller.database_deleted.connect(lambda x: log.info(f"database_deleted: {x}"))
    database_controller.database_changed.connect(lambda x: log.info(f"database_changed: {x}"))

    activity_controller.activity_changed.connect(lambda x: log.info(f"activity_changed: {x}"))
    activity_controller.activity_deleted.connect(lambda x: log.info(f"activity_deleted: {x}"))

    exchange_controller.new_exchange.connect(lambda x: log.info(f"new_exchange: {x}"))
    exchange_controller.exchange_changed.connect(lambda x: log.info(f"exchange_changed: {x}"))
    exchange_controller.exchange_deleted.connect(lambda x: log.info(f"exchange_deleted: {x}"))

def load_settings() -> None:
    if ab_settings.settings:
        log.info("Loading user settings:")
        project_controller.switch_dir(ab_settings.current_bw_dir)
        project_controller.set_current(ab_settings.startup_project)
    log.info(f'Brightway2 data directory: {project_controller.base_dir}')
    log.info(f'Brightway2 active project: {project_controller.current}')


def run_activity_browser():
    log.info(f'The Activity Browser log file can be found at {log.log_file_path()}')
    log.info(f'Activity Browser version: {version}')

    application.main_window = MainWindow(application)
    load_settings()
    controller_logger()
    application.show()

    def exception_hook(*args):
        log.warning(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(application.exec_())
