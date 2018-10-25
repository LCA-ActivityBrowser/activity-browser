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
        # signals.lca_results_tabs_changed.connect(self.update_self)
        signals.show_tab_or_hide_when_empty.connect(self.show_tab_or_hide_when_empty)

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
                print("-hiding tab:", tab_name)
                tab.setVisible(False)
                self.setCurrentIndex(current_index)
                self.removeTab(self.indexOf(tab))

    def show_tab(self, tab_name):
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            print("+showing tab:", tab_name)
            tab.setVisible(True)
            self.addTab(tab, tab_name)
            self.select_tab(tab)

    def add_tab(self):
        """To add some functionality on top of the default addTab by Qt."""
        pass

    def remove_tab(self):
        pass

    def get_tab_name(self, obj):
        tab_names = [name for name, o in self.tabs.items() if o == obj]
        if len(tab_names) == 1:
            return tab_names[0]
        else:
            print("Warning: found", len(tab_names), "occurences of this object.")

    def show_tab_or_hide_when_empty(self):
        print("\nChecking for empty tabs:")
        for tab_name, tab in self.tabs.items():
            print("Tab:", self.get_tab_name(tab), "...")
            if hasattr(tab, "tabs"):
                print("Subtabs:", tab.tabs.keys())
                if not tab.tabs:
                    self.hide_tab(tab_name)
                else:
                    self.show_tab(tab_name)


    # def hide_if_no_tabs(self):
    #     print("Hide if no tabs:", self.tabText(self.currentIndex()))
    #     for tab_name, tab in self.tabs.items():
    #         if hasattr(tab, "tabs"):
    #             print("Tab:", tab_name, "Subtabs:", tab.tabs)