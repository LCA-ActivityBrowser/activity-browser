# -*- coding: utf-8 -*-
from PySide2 import QtWidgets

from ...signals import signals


class ABTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(ABTab, self).__init__(parent)
        self.setMovable(True)
        self.tabs = dict()  # keys: tab name; values: tab widget

        # signals
        signals.show_tab.connect(self.show_tab)
        signals.hide_tab.connect(self.hide_tab)
        signals.toggle_show_or_hide_tab.connect(self.toggle_tab_visibility)
        signals.hide_when_empty.connect(self.hide_when_empty)

    def add_tab(self, obj, tab_name):
        """Default addTab method and add item to self.tabs
        """
        self.tabs[tab_name] = obj
        self.addTab(obj, tab_name)

    def select_tab(self, obj):
        """Brings tab to focus."""
        self.setCurrentIndex(self.indexOf(obj))

    def toggle_tab_visibility(self, tab_name):
        """Show or hide a tab.
        Used, e.g. for Windows-->show/hide menu."""
        if tab_name in self.tabs:
            if self.indexOf(self.tabs[tab_name]) != -1:
                self.hide_tab(tab_name)
            else:
                self.show_tab(tab_name)

    def hide_tab(self, tab_name, current_index=0):
        """Hides tab, but does not delete the QTabWidget itself."""
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            if self.indexOf(tab) != -1:
                print("-hiding tab:", tab_name)
                tab.setVisible(False)
                # Only explicitly alter the tab index if we're hiding the
                # current tab itself.
                if self.currentIndex() == self.indexOf(tab):
                    self.setCurrentIndex(current_index)
                self.removeTab(self.indexOf(tab))

    def show_tab(self, tab_name):
        """Makes existing tab visible."""
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            print("+showing tab:", tab_name)
            tab.setVisible(True)
            self.addTab(tab, tab_name)
            self.select_tab(tab)

    def get_tab_name(self, obj):
        """Returns the name of a tab."""
        tab_names = [name for name, o in self.tabs.items() if o == obj]
        if len(tab_names) == 1:
            return tab_names[0]
        else:
            print("Warning: found", len(tab_names), "occurences of this object.")

    def hide_when_empty(self):
        """Show tab if it has sub-tabs (not empty) or hide if it has no sub-tabs (empty)."""
        # print("\nChecking for empty tabs:")
        for tab_name, tab in self.tabs.items():
            # print("Tab:", self.get_tab_name(tab), "...")
            if hasattr(tab, "tabs"):
                # print("Subtabs:", tab.tabs.keys())
                if not tab.tabs:
                    self.hide_tab(tab_name)
                # else:  # leads to strange behaviour of setCurrentIndex/select_tab
                #     self.show_tab(tab_name)

    def close_tab(self, index):
        """Close tab by index."""
        widget = self.widget(index)
        tab_name = self.get_tab_name(widget)
        # print("Closing tab:", tab_name)
        if widget in self.tabs.values():
            del self.tabs[tab_name]
            widget.deleteLater()
            self.removeTab(index)
        signals.hide_when_empty.emit()  # needs to be a signal as we want the super-tab to receive this...

    def close_tab_by_tab_name(self, tab_name):
        """Close tab by tab name (key in self.tabs)."""
        if tab_name in self.tabs:
            self.close_tab(self.indexOf(self.tabs[tab_name]))

    def close_all(self):
        """Close all tabs."""
        open_tab_count = len(self.tabs)
        for i in reversed(range(open_tab_count)):
            self.close_tab(i)