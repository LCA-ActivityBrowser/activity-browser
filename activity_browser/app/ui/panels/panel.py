# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from ...signals import signals


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

