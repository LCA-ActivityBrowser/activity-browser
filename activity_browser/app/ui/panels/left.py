# -*- coding: utf-8 -*-
from .panel import Panel
from ..web.webutils import RestrictedWebViewWidget
from ..tabs import (ProjectTab, MethodsTab)
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

        # add tabs
        self.addTab(self.welcome_tab, 'Welcome')
        self.addTab(self.project_tab, 'Project')
        self.addTab(self.methods_tab, 'Impact Categories')

        # signals
        self.currentChanged.connect(self.remove_welcome_tab)


    def remove_welcome_tab(self):
        if self.indexOf(self.welcome_tab) != -1:
            self.removeTab(self.indexOf(self.welcome_tab))
