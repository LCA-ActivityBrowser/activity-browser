# -*- coding: utf-8 -*-
from .panel import Panel, ActivitiesPanel, MethodsPanel
from ..web.webutils import RestrictedWebViewWidget
from ..web.graphnav import GraphNavigatorWidget
from .. import activity_cache
from ..tabs import LCASetupTab
from ...signals import signals
from .... import PACKAGE_DIRECTORY


class LeftPanel(Panel):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)
        # Tabs
        self.welcome_tab = RestrictedWebViewWidget(
            html_file=PACKAGE_DIRECTORY + r'/app/ui/web/startscreen/welcome.html'
        )
        self.method_panel = MethodsPanel(self)
        self.LCA_setup_tab = LCASetupTab(self)
        self.act_panel = ActivitiesPanel(self)
        self.graph_navigator_tab = GraphNavigatorWidget()

        # add tabs
        self.addTab(self.welcome_tab, 'Welcome')
        self.addTab(self.LCA_setup_tab, 'LCA Setup')
        self.addTab(self.graph_navigator_tab, 'Graph-Navigator')

        # signals
        signals.activity_tabs_changed.connect(self.update_activity_panel)
        self.currentChanged.connect(self.remove_welcome_tab)
        signals.method_tabs_changed.connect(self.update_method_panel)

    def update_method_panel(self):
        if self.method_panel.tab_dict:
            if self.indexOf(self.method_panel) == -1:
                self.addTab(self.method_panel, 'Characterization Factors')
            self.select_tab(self.method_panel)
        else:
            self.removeTab(self.indexOf(self.method_panel))
            self.setCurrentIndex(0)

    def update_activity_panel(self):
        if len(activity_cache):
            self.addTab(self.act_panel, 'Activities')
            self.select_tab(self.act_panel)
        else:
            self.removeTab(self.indexOf(self.act_panel))
            self.setCurrentIndex(0)

    def remove_welcome_tab(self):
        if self.indexOf(self.welcome_tab) != -1:
            self.removeTab(self.indexOf(self.welcome_tab))
