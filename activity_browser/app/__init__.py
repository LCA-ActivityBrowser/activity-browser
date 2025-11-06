# -*- coding: utf-8 -*-
__all__ = ["panes", "pages", "application", "signals", "metadata", "main_window"]

from activity_browser.ui.core.application import ABApplication
from .main_window import MainWindow
from .signals import ABSignals

application = ABApplication()

signals = ABSignals()

main_window = MainWindow()
application.main_window = main_window

from activity_browser.bwutils import MetaDataStore
metadata = MetaDataStore()
