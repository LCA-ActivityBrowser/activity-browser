# -*- coding: utf-8 -*-
from .panel import ABTab
from ..web.webutils import RestrictedWebViewWidget
from ..tabs import (ProjectTab, MethodsTab, HistoryTab)
from ...signals import signals
from .... import PACKAGE_DIRECTORY


class LeftPanel(ABTab):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)
        # Tabs
        self.welcome_tab = RestrictedWebViewWidget(
            html_file=PACKAGE_DIRECTORY + r'/app/ui/web/startscreen/welcome.html'
        )

        # instantiate tabs
        self.project_tab = ProjectTab(self)
        self.methods_tab = MethodsTab(self)
        self.history_tab = HistoryTab(self)
        self.history_tab.setVisible(False)

        # add tabs
        self.addTab(self.welcome_tab, 'Welcome')
        self.addTab(self.project_tab, 'Project')
        self.addTab(self.methods_tab, 'Impact Categories')
        # self.addTab(self.history_tab, 'Project History')

        # signals
        self.currentChanged.connect(self.remove_welcome_tab)
        signals.show_history.connect(self.toggle_history_visibility)

    def remove_welcome_tab(self):
        if self.indexOf(self.welcome_tab) != -1:
            self.removeTab(self.indexOf(self.welcome_tab))

    def toggle_history_visibility(self):
        """Show or hide the history tab. This could be """
        if self.history_tab.isVisible():
            print("adding history tab")
            self.history_tab.setVisible(False)
            self.removeTab(self.indexOf(self.history_tab))
            self.setCurrentIndex(0)
        else:
            print("removing history tab")
            self.history_tab.setVisible(True)
            self.addTab(self.history_tab, 'Project History')
            self.select_tab(self.history_tab)
