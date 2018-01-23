# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtWidgets

from .. import activity_cache
from ..tabs import ActivityDetailsTab
from ..utils import get_name
from ...signals import signals


class Panel(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(Panel, self).__init__(parent)
        self.setMovable(True)

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))


class ActivitiesPanel(Panel):
    def __init__(self, parent=None):
        super(Panel, self).__init__(parent)
        self.side = 'activities'
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)

        signals.open_activity_tab.connect(self.open_new_activity_tab)
        signals.activity_modified.connect(self.update_activity_name)

    def update_activity_name(self, key, field, value):
        if key in activity_cache and field == 'name':
            try:
                index = self.indexOf(activity_cache[key])
                self.setTabText(index, value)
            except:
                pass

    def open_new_activity_tab(self, side, key):
        if side == self.side:
            if key in activity_cache:
                self.select_tab(activity_cache[key])
            else:
                new_tab = ActivityDetailsTab(self)
                new_tab.populate(key)
                activity_cache[key] = new_tab
                self.addTab(new_tab, get_name(bw.get_activity(key)))
                self.select_tab(new_tab)
            signals.activity_tabs_changed.emit()

    def close_tab(self, index):
        widget = self.widget(index)
        if isinstance(widget, ActivityDetailsTab):
            assert widget.activity in activity_cache
            del activity_cache[widget.activity]
        widget.deleteLater()
        self.removeTab(index)
        signals.activity_tabs_changed.emit()
