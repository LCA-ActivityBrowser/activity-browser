# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from ..tabs import ActivityDetailsTab
from ..utils import get_name
from brightway2 import *
from PyQt4 import QtGui


class Panel(QtGui.QTabWidget):
    def __init__(self, parent=None):
        super(Panel, self).__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)

        signals.open_activity_tab.connect(self.open_new_activity_tab)

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))

    def open_new_activity_tab(self, side, key):
        if side == self.side:
            new_tab = ActivityDetailsTab(self)
            new_tab.populate(key)
            self.addTab(new_tab, get_name(get_activity(key)))
            self.select_tab(new_tab)

    def close_tab(self, index):
        if index >= 3:
            # TODO: Should look up by tab class, not index, as tabs are movable
            widget = self.widget(index)
            widget.deleteLater()
            self.removeTab(index)
