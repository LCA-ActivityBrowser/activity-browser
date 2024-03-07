# -*- coding: utf-8 -*-
import sys

from .logger import log, exception_hook, file_handler
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .controllers import *
from .info import __version__ as version
from .layouts.main import MainWindow
from .plugin import Plugin


def run_activity_browser():
    log.info(f'Activity Browser version: {version}')
    log.info(f'The log file can be found at {file_handler.filepath}')

    application.main_window = MainWindow(application)
    project_controller.load_settings()
    application.show()

    sys.excepthook = exception_hook

    sys.exit(application.exec_())
