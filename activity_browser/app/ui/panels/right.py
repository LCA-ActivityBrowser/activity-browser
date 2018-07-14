# -*- coding: utf-8 -*-
from .panel import Panel, ActivitiesPanel, MethodsPanel
from ..tabs import (
    LCASetupTab,
    ActivityDetailsTab,
    HistoryTab,
    ImpactAssessmentTab,
)
from ...signals import signals
from .. import activity_cache

class RightPanel(Panel):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.method_panel = MethodsPanel(self)
        self.act_panel = ActivitiesPanel(self)

        self.LCA_setup_tab = LCASetupTab(self)
        self.history_tab = HistoryTab(self)
        self.lca_results_tab = ImpactAssessmentTab(self)

        # addtabs
        self.addTab(self.LCA_setup_tab, 'LCA Setup')
        self.addTab(self.history_tab, 'History')

        # Signals
        signals.activity_tabs_changed.connect(self.update_activity_panel)
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


    def close_tab(self, index):
        if index >= 3:
            # TODO: Should look up by tab class, not index, as tabs are movable
            widget = self.widget(index)
            if isinstance(widget, ActivityDetailsTab):
                assert widget.activity in activity_cache
                del activity_cache[widget.activity]
            widget.deleteLater()
            self.removeTab(index)

        self.setCurrentIndex(0)
