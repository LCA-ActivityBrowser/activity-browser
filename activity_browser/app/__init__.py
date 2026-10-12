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

# Open the settings startup project before UI listens to project.changed.
# Otherwise Brightway stays on ``default`` until apply_settings, and the switch
# rebuilds every pane while MetaDataStore loads (multi-second on large projects).
if not os.environ.get("AB_SKIP_SETTINGS_ON_STARTUP"):
    activate_configured_project(settings)

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
