# -*- coding: utf-8 -*-
import os

from .panel import Panel, ActivitiesPanel
from ..web.webutils import SimpleWebPageWidget
from .. import activity_cache
from ..tabs import CalculationSetupTab, CFsTab
from ...signals import signals
from .... import PACKAGE_DIRECTORY

class LeftPanel(Panel):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)
        # Tabs
        self.welcome_tab = SimpleWebPageWidget(html_file=PACKAGE_DIRECTORY+r'/app/ui/web/startscreen/startscreen.html')
        self.cfs_tab = CFsTab(self)
        self.cs_tab = CalculationSetupTab(self)
        self.act_panel = ActivitiesPanel(self)
        # add tabs
        self.addTab(self.welcome_tab, 'Welcome')
        self.addTab(self.cfs_tab, 'LCIA CFs')
        self.addTab(self.cs_tab, 'LCA Calculations')

        # self.setTabsClosable(True)

        signals.activity_tabs_changed.connect(self.update_activity_panel)

    def update_activity_panel(self):
        if len(activity_cache):
            self.addTab(self.act_panel, 'Activities')
            self.select_tab(self.act_panel)
        else:
            self.removeTab(self.indexOf(self.act_panel))
            self.setCurrentIndex(0)
