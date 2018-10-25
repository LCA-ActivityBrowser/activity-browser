# -*- coding: utf-8 -*-
from .panel import ABTab
from ..web.webutils import RestrictedWebViewWidget
from ..tabs import (ProjectTab, MethodsTab, HistoryTab)
from .... import PACKAGE_DIRECTORY


class LeftPanel(ABTab):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)

        self.tabs = {
            "Welcome": RestrictedWebViewWidget(html_file=PACKAGE_DIRECTORY + r'/app/ui/web/startscreen/welcome.html'),
            "Project": ProjectTab(self),
            "Impact Categories": MethodsTab(self),
            "Project History": HistoryTab(self),
        }

        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)

        # tabs hidden at start
        self.hide_tab("Project History")

        self.connect_signals()

    def connect_signals(self):
        self.currentChanged.connect(
            lambda i, x="Welcome": self.hide_tab(x, current_index=i)
        )

