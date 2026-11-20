# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets
from logging import getLogger

from activity_browser import signals

log = getLogger(__name__)


class TabId:
    """Stable identifiers for the built-in top-level tabs.

    These values are sent through the global tab signals and must therefore
    never be translated.  User-visible tab labels are stored separately by
    :class:`ABTab`.
    """

    PROJECT = "left.project"
    IMPACT_CATEGORIES = "left.impact_categories"
    HISTORY = "left.history"

    WELCOME = "right.welcome"
    CHARACTERIZATION_FACTORS = "right.characterization_factors"
    ACTIVITY_DETAILS = "right.activity_details"
    LCA_SETUP = "right.lca_setup"
    GRAPH_EXPLORER = "right.graph_explorer"
    LCA_RESULTS = "right.lca_results"
    PARAMETERS = "right.parameters"


class ABTab(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super(ABTab, self).__init__(parent)
        self.setMovable(True)
        # ``tabs`` is keyed by stable identifiers.  Display labels live in a
        # separate mapping so translating a label can never break tab logic.
        self.tabs = dict()
        self.tab_labels = dict()
        self.tab_aliases = dict()

        # signals
        signals.show_tab.connect(self.show_tab)
        signals.hide_tab.connect(self.hide_tab)
        signals.toggle_show_or_hide_tab.connect(self.toggle_tab_visibility)
        signals.hide_when_empty.connect(self.hide_when_empty)
        self.connect(
            self, QtCore.SIGNAL("currentChanged(int)"), self.current_index_changed
        )

    def current_index_changed(self, current_index: int):
        """Optional function to accept the index of the selected tab."""
        pass  # NotImplementedError is not used as this function gets called often and not neccecarily used.

    def add_tab(self, obj, tab_id, tab_label=None, aliases=()):
        """Add a tab using a stable ID and an independently translated label.

        ``aliases`` keeps compatibility with older signal emitters which used
        the English label as the tab identifier.
        """
        label = tab_label if tab_label is not None else str(tab_id)
        self.tabs[tab_id] = obj
        self.tab_labels[tab_id] = label
        self.tab_aliases[tab_id] = tab_id
        self.tab_aliases[label] = tab_id
        for alias in aliases:
            self.tab_aliases[alias] = tab_id
        return self.addTab(obj, label)

    def _resolve_tab_id(self, tab_id):
        """Resolve a stable tab ID, translated label, or legacy English label."""
        try:
            if tab_id in self.tabs:
                return tab_id
            return self.tab_aliases.get(tab_id)
        except TypeError:
            return None

    def select_tab(self, obj):
        """Brings tab to focus."""
        self.setCurrentIndex(self.indexOf(obj))

    def toggle_tab_visibility(self, tab_id):
        """Show or hide a tab.
        Used, e.g. for Windows-->show/hide menu."""
        tab_id = self._resolve_tab_id(tab_id)
        if tab_id is not None:
            if self.indexOf(self.tabs[tab_id]) != -1:
                self.hide_tab(tab_id)
            else:
                self.show_tab(tab_id)

    def hide_tab(self, tab_id, current_index=0):
        """Hides tab, but does not delete the QTabWidget itself."""
        tab_id = self._resolve_tab_id(tab_id)
        if tab_id is not None:
            tab = self.tabs[tab_id]
            if self.indexOf(tab) != -1:
                log.debug("Hiding tab: %s", tab_id)
                tab.setVisible(False)
                # Only explicitly alter the tab index if we're hiding the
                # current tab itself.
                if self.currentIndex() == self.indexOf(tab):
                    self.setCurrentIndex(current_index)
                self.removeTab(self.indexOf(tab))

    def show_tab(self, tab_id):
        """Makes existing tab visible."""
        tab_id = self._resolve_tab_id(tab_id)
        if tab_id is not None:
            tab = self.tabs[tab_id]
            log.info("+showing tab: %s", tab_id)
            tab.setVisible(True)
            self.addTab(tab, self.tab_labels.get(tab_id, str(tab_id)))
            self.select_tab(tab)

    def get_tab_name(self, obj):
        """Returns the name of a tab."""
        tab_names = [name for name, o in self.tabs.items() if o == obj]
        if len(tab_names) == 1:
            return tab_names[0]
        else:
            log.warning(f"found {len(tab_names)} occurrences of this object.")

    def get_tab_name_from_index(self, index):
        """Return the stable ID of a tab based on its visible index."""
        widget = self.widget(index)
        if widget is not None:
            return self.get_tab_name(widget)
        log.warning("Did not find instance of tab")

    def hide_when_empty(self):
        """Show tab if it has sub-tabs (not empty) or hide if it has no sub-tabs (empty)."""
        for tab_id, tab in self.tabs.items():
            if hasattr(tab, "tabs"):
                if not tab.tabs:
                    self.hide_tab(tab_id)
                # else:  # leads to strange behaviour of setCurrentIndex/select_tab
                #     self.show_tab(tab_name)

    def close_tab(self, index):
        """Close tab by index."""
        widget = self.widget(index)
        tab_id = self.get_tab_name(widget)
        if widget in self.tabs.values():
            del self.tabs[tab_id]
            self.tab_labels.pop(tab_id, None)
            self.tab_aliases = {
                alias: target
                for alias, target in self.tab_aliases.items()
                if target != tab_id
            }
            widget.deleteLater()
        self.removeTab(index)
        signals.hide_when_empty.emit()  # needs to be a signal as we want the super-tab to receive this...

    def close_tab_by_tab_name(self, tab_id):
        """Close a tab by stable ID (legacy labels are also accepted)."""
        tab_id = self._resolve_tab_id(tab_id)
        if tab_id is not None:
            self.close_tab(self.indexOf(self.tabs[tab_id]))

    def close_all(self):
        """Close all tabs."""
        open_tab_count = len(self.tabs)
        for i in reversed(range(open_tab_count)):
            self.close_tab(i)
