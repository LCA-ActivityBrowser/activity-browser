# -*- coding: utf-8 -*-
import sys
import traceback

from .logger import log
from .application import application
from .signals import signals
from .info import __version__ as version
from .settings import ab_settings, project_settings
from .controllers import controllers
from .layouts.main import MainWindow
from .plugin import Plugin


def run_activity_browser():
    log.info(f'The Activity Browser log file can be found at {log.log_file_path()}')
    log.info(f'Activity Browser version: {version}')

    application.main_window = MainWindow(application)
    application.set_controllers(controllers)
    application.show()

    def exception_hook(*args):
        log.warning(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(application.exec_())
