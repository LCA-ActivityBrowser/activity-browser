# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import activity_cache
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
            if key in activity_cache:
                self.select_tab(activity_cache[key])
            else:
                new_tab = ActivityDetailsTab(self)
                new_tab.populate(key)
                activity_cache[key] = new_tab
                self.addTab(new_tab, get_name(get_activity(key)))
                self.select_tab(new_tab)

    def close_tab(self, index):
        if index >= 3:
            # TODO: Should look up by tab class, not index, as tabs are movable
            widget = self.widget(index)
            if isinstance(widget, ActivityDetailsTab):
                assert widget.activity in activity_cache
                del activity_cache[widget.activity]
            widget.deleteLater()
            self.removeTab(index)
