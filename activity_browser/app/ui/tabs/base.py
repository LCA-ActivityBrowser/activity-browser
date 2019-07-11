# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget


class BaseRightTab(QWidget):
    """ Extremely basic widget, to be created and used inside a QTabWidget
    """
    def __init__(self, parent):
        super().__init__(parent)
        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        """ Used by child classes to wire up specific functionality to signals

        Should only be used during init
        """
        raise NotImplementedError

    def _construct_layout(self):
        """ Used by child classes to construct the initial layout of the widget

        Usually, the function should end with a self.setLayout() call.

        Should only be used during init
        """
        raise NotImplementedError


class BaseRightTabbedTab(QTabWidget):
    """ Extremely basic tab widget, holds one or more QWidgets as tabs
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.tabs = {}
        self._connect_signals()

    def _connect_signals(self):
        """ Used by child classes to wire up specific functionality to signals
        or held tabs.
        """
        raise NotImplementedError
