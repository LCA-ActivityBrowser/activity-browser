# -*- coding: utf-8 -*-
from .panel import Panel, ActivitiesPanel, MethodsPanel
from ..web.webutils import RestrictedWebViewWidget
from ..tabs import (ProjectTab, MethodsTab, HistoryTab)
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

        self.methods_tab = MethodsTab(self)
        self.project_tab = ProjectTab(self)
        self.history_tab = HistoryTab(self)
        self.method_panel = MethodsPanel(self)
        self.LCA_setup_tab = LCASetupTab(self)
        self.act_panel = ActivitiesPanel(self)
        self.graph_navigator_tab = GraphNavigatorWidget()

        # add tabs
        self.addTab(self.welcome_tab, 'Welcome')
        self.addTab(self.LCA_setup_tab, 'LCA Setup')
        self.addTab(self.graph_navigator_tab, 'Graph-Navigator')
        self.addTab(self.project_tab, 'Project')
        self.addTab(self.methods_tab, 'Impact Categories')
        self.addTab(self.history_tab, 'Project History')

        # signals
        self.currentChanged.connect(self.remove_welcome_tab)


    def remove_welcome_tab(self):
        if self.indexOf(self.welcome_tab) != -1:
            self.removeTab(self.indexOf(self.welcome_tab))
