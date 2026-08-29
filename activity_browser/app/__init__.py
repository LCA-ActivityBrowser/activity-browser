# -*- coding: utf-8 -*-
__all__ = ["panes", "pages", "application", "signals", "metadata", "main_window", "actions"]

import os

from activity_browser.ui.core.application import ABApplication
from activity_browser.bwutils.metadata import MetaDataStore
from activity_browser.bwutils.settings import Settings, activate_configured_project
from .main import MainWindow

application = ABApplication()
settings = Settings()
metadata = MetaDataStore(application)

# Before ABSignals/MainWindow: open the configured project so the later
# apply_settings(load=True) only syncs panes (no second project_changed).
_skip_startup = bool(os.environ.get("AB_SKIP_SETTINGS_ON_STARTUP"))
if not _skip_startup:
    activate_configured_project(settings)

# modules dependent on application instance
from .signalling import ABSignals

signals = ABSignals()

# modules dependent on application and signals
from . import actions
from . import panes
from . import pages
from . import dialogs

# Activate enabled plugins before MainWindow so contributions join first paint.
from activity_browser.plugins.loader import load_and_activate_plugins

load_and_activate_plugins(application=application, signals=signals, settings=settings)

main_window = MainWindow()
application.main_window = main_window

if not _skip_startup:
    main_window.apply_settings(load=True)  # Ensure settings are applied at startup
