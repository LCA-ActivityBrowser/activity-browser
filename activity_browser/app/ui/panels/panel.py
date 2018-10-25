# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtWidgets

from .. import activity_cache
from ..tabs import ActivityTab, CFsTab
from ...bwutils.commontasks import get_activity_name
from ...signals import signals
from ...settings import user_project_settings

class ABTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(ABTab, self).__init__(parent)
        self.setMovable(True)
        self.tabs = dict()  # keys: tab name; values: tab widget

        # signals
        signals.toggle_show_or_hide_tab.connect(self.toggle_tab_visibility)
        signals.show_tab.connect(self.show_tab)
        signals.hide_tab.connect(self.hide_tab)

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))

    def toggle_tab_visibility(self, tab_name):
        """Show or hide a tab."""
        if tab_name in self.tabs:
            if self.indexOf(self.tabs[tab_name]) != -1:
                self.hide_tab(tab_name)
            else:
                self.show_tab(tab_name)

    def hide_tab(self, tab_name, current_index=0):
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            if self.indexOf(tab) != -1:
                print("hiding tab:", tab_name)
                tab.setVisible(False)
                self.setCurrentIndex(current_index)
                self.removeTab(self.indexOf(tab))

    def show_tab(self, tab_name):
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            print("showing tab:", tab_name)
            tab.setVisible(True)
            self.addTab(tab, tab_name)
            self.select_tab(tab)

    def add_tab(self):
        """To add some functionality on top of the default addTab by Qt."""
        pass

    def remove_tab(self):
        pass


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
        self.setTabsClosable(True)
        self.connect_signals()

    def connect_signals(self):
        signals.open_activity_tab.connect(self.open_activity_tab)
        signals.activity_modified.connect(self.update_activity_name)
        self.tabCloseRequested.connect(self.close_tab)
        signals.project_selected.connect(self.close_all_activity_tabs)

    def open_activity_tab(self, key):
        """Opens new ActivityTab of focuses on already open one."""

        if key in activity_cache:
            self.select_tab(activity_cache[key])
        else:
            databases_read_only_settings = user_project_settings.settings.get('read-only-databases', {})
            database_read_only = databases_read_only_settings.get(key[0], True)
            new_tab = ActivityTab(key, parent=self, read_only=True, db_read_only=database_read_only)
            activity_cache[key] = new_tab

            # get_name returns the act name using bw-specific code, modified to return 30 chars.
            self.addTab(new_tab, get_activity_name(bw.get_activity(key), str_length=30))
            self.select_tab(new_tab)

            # hovering on the tab shows the full name, in case it's truncated in the tabbar at the top
            # new_tab.setToolTip(bw.get_activity(key).as_dict()['name'])

        signals.activity_tabs_changed.emit()

    def update_activity_name(self, key, field, value):
        if key in activity_cache and field == 'name':
            try:
                index = self.indexOf(activity_cache[key])
                self.setTabText(index, value)
            except:
                pass

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
