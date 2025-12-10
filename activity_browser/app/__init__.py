# -*- coding: utf-8 -*-
__all__ = ["panes", "pages", "application", "signals", "metadata", "main_window", "actions"]

import os

from activity_browser.ui.core.application import ABApplication
from activity_browser.bwutils.metadata import MetaDataStore
from activity_browser.bwutils.settings import Settings
from .main import MainWindow

application = ABApplication()
metadata = MetaDataStore()
settings = Settings()

# modules dependent on application instance
from .signalling import ABSignals

signals = ABSignals()

# modules dependent on application and signals
from . import actions
from . import panes
from . import pages
from . import dialogs

main_window = MainWindow()
application.main_window = main_window

if not os.environ.get("AB_SKIP_SETTINGS_ON_STARTUP"):
    main_window.apply_settings(load=True)  # Ensure settings are applied at startup

