from pathlib import Path
from logging import getLogger

from PySide2.QtWidgets import QVBoxLayout

from activity_browser import signals
from activity_browser.i18n import _
from activity_browser.mod import bw2data as bd

from ...bwutils.commontasks import get_activity_name
from ...ui.web import GraphNavigatorWidget, RestrictedWebViewWidget
from ..tabs import (ActivitiesTab, CharacterizationFactorsTab, LCAResultsTab,
                    LCASetupTab, ParametersTab)
from .panel import ABTab, TabId

log = getLogger(__name__)


class RightPanel(ABTab):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)
        package_dir = Path(__file__).resolve().parents[2]
        html_file = str(package_dir.joinpath("static", "startscreen", "welcome.html"))
        self.tab_order = {}
        tabs = (
            (TabId.WELCOME, "Welcome", RestrictedWebViewWidget(html_file=html_file)),
            (
                TabId.CHARACTERIZATION_FACTORS,
                "Characterization Factors",
                CharacterizationFactorsTab(self),
            ),
            (TabId.ACTIVITY_DETAILS, "Activity Details", ActivitiesTab(self)),
            (TabId.LCA_SETUP, "LCA Setup", LCASetupTab(self)),
            (TabId.GRAPH_EXPLORER, "Graph Explorer", GraphExplorerTab(self)),
            (TabId.LCA_RESULTS, "LCA results", LCAResultsTab(self)),
            (TabId.PARAMETERS, "Parameters", ParametersTab(self)),
        )

        for tab_id, source_label, tab in tabs:
            self.tab_order[tab_id] = self.add_tab(
                tab, tab_id, _(source_label), aliases=(source_label,)
            )

        # tabs hidden at start
        for tab_id in [
            TabId.ACTIVITY_DETAILS,
            TabId.CHARACTERIZATION_FACTORS,
            TabId.GRAPH_EXPLORER,
            TabId.LCA_RESULTS,
        ]:
            self.hide_tab(tab_id)

    def show_tab(self, tab_id):
        """Re-inserts tab at the initial location.

        This avoids constantly re-ordering the mayor tabs.
        """
        tab_id = self._resolve_tab_id(tab_id)
        if tab_id is not None:
            tab = self.tabs[tab_id]
            log.info("+showing tab: %s", tab_id)
            tab.setVisible(True)
            self.insertTab(
                self.tab_order[tab_id], tab, self.tab_labels.get(tab_id, str(tab_id))
            )
            self.select_tab(tab)


class GraphExplorerTab(ABTab):
    def __init__(self, parent):
        super(GraphExplorerTab, self).__init__(parent)

        self.setMovable(True)
        self.setTabsClosable(True)
        # self.setTabShape(1)  # Triangular-shaped Tabs

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        self.tabCloseRequested.connect(self.close_tab)
        bd.projects.current_changed.connect(self.close_all)
        signals.open_activity_graph_tab.connect(self.add_tab)

    def add_tab(self, key, select=True):
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            log.info("adding graph tab")
            new_tab = GraphNavigatorWidget(self, key=key)
            self.tabs[key] = new_tab
            self.addTab(new_tab, new_tab.objectName())

            new_tab.objectNameChanged.connect(
                lambda name: self.setTabText(self.indexOf(new_tab), name)
            )

        else:
            tab = self.tabs[key]
            tab.new_graph(key)

        if select:
            self.select_tab(self.tabs[key])
            signals.show_tab.emit(TabId.GRAPH_EXPLORER)
