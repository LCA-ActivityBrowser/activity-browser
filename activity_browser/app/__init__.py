# -*- coding: utf-8 -*-
__all__ = [
    "panes",
    "pages",
    "application",
    "signals",
    "metadata",
    "main_window",
    "actions",
    "create_main_window",
]

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

main_window = None


def create_main_window(*, load_settings: bool | None = None):
    """Create ``main_window`` after loading plugins and applying settings.

    Startup is split in two phases:

    1. ``import activity_browser.app`` — singletons only (``application``,
       ``signals``, ``settings``); ``main_window`` stays ``None``.
    2. ``create_main_window()`` — activate plugins, construct ``MainWindow``,
       optionally ``apply_settings(load=True)``.

    Call from ``__main__`` after deferred imports, or from tests that need a
    full UI session. Safe to call more than once (returns the existing window).
    """
    global main_window

    if main_window is not None:
        return main_window

    from activity_browser.plugins.loader import load_and_activate_plugins

    load_and_activate_plugins(application=application, signals=signals, settings=settings)

    main_window = MainWindow()
    application.main_window = main_window

    if load_settings is None:
        load_settings = not os.environ.get("AB_SKIP_SETTINGS_ON_STARTUP")
    if load_settings:
        main_window.apply_settings(load=True)

    return main_window
