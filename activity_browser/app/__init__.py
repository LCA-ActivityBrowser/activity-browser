# -*- coding: utf-8 -*-
__all__ = ["panes", "pages", "application", "signals", "metadata", "main_window"]

from activity_browser.bwutils import MetaDataStore

from .main_window import MainWindow
from .application import ABApplication
from .signals import ABSignals

application = ABApplication()

signals = ABSignals()

main_window = MainWindow()
application.main_window = main_window

metadata = MetaDataStore()
