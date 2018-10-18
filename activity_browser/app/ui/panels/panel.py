# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtWidgets

from .. import activity_cache
from ..tabs import ActivityTab, CFsTab
from ..utils import get_name
from ...signals import signals
from ...settings import user_project_settings

class ABTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(ABTab, self).__init__(parent)
        self.setMovable(True)

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))


class CharacterizationFactorsTab(ABTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.tab_dict = {}
        signals.method_selected.connect(self.open_method_tab)
        signals.project_selected.connect(self.close_all)

    def open_method_tab(self, method):
        if method not in self.tab_dict:
            tab = CFsTab(self, method)
            full_tab_label = ' '.join(method)
            label = full_tab_label[:min((10, len(full_tab_label)))] + '..'
            self.tab_dict[method] = tab
            self.addTab(tab, label)
        else:
            tab = self.tab_dict[method]

        self.select_tab(tab)
        signals.method_tabs_changed.emit()

    def close_tab(self, index):
        tab = self.widget(index)
        del self.tab_dict[tab.method]
        self.removeTab(index)
        signals.method_tabs_changed.emit()

    def close_all(self):
        self.clear()
        self.tab_dict = {}
        signals.method_tabs_changed.emit()


class ActivitiesTab(ABTab):
    def __init__(self, parent=None):
        super(ABTab, self).__init__(parent)
        self.side = 'activities'
        self.setMovable(True)
        self.setTabsClosable(True)
        self.connect_signals()

    def update_activity_name(self, key, field, value):
        if key in activity_cache and field == 'name':
            try:
                index = self.indexOf(activity_cache[key])
                self.setTabText(index, value)
            except:
                pass

    def open_activity_tab(self, side, key):
        """check if activity open as ActivityTab and focus if so
        else create a new ActivityTab for activity and focus it"""

        if side == self.side:
            if key in activity_cache:
                self.select_tab(activity_cache[key])
            else:
                databases_read_only_settings = user_project_settings.settings.get('read-only-databases', {})

                database_read_only = databases_read_only_settings.get(key[0], True)
                # print(databases_read_only_settings)
                # print(database_read_only)
                act_dict = bw.get_activity(key).as_dict()
                act_name = act_dict['name']

                new_tab = ActivityTab(key, parent=self, read_only=True, db_read_only=database_read_only)


                # hovering on the tab shows the full name, in case it's truncated in the tabbar at the top
                new_tab.setToolTip(act_name)

                activity_cache[key] = new_tab

                # get_name returns the act name using bw-specific code, modified to return 30 chars.
                self.addTab(new_tab, get_name(bw.get_activity(key), str_length=30))
                self.select_tab(new_tab)

            signals.activity_tabs_changed.emit()

    def close_tab(self, index):
        widget = self.widget(index)
        if isinstance(widget, ActivityTab):
            assert widget.activity in activity_cache
            del activity_cache[widget.activity]
        widget.deleteLater()
        self.removeTab(index)
        signals.activity_tabs_changed.emit()

    def close_all_activity_tabs(self):
        open_tab_count = len(activity_cache)
        for i in reversed(range(open_tab_count)):
            self.close_tab(i)

    def connect_signals(self):
        self.tabCloseRequested.connect(self.close_tab)
        signals.open_activity_tab.connect(self.open_activity_tab)
        signals.activity_modified.connect(self.update_activity_name)
        signals.project_selected.connect(self.close_all_activity_tabs)