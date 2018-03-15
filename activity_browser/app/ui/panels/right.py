# -*- coding: utf-8 -*-
from .panel import Panel
from .. import activity_cache
from ..tabs import (
    ActivityDetailsTab,
    HistoryTab,
    ImpactAssessmentTab,
    MethodsTab,
    ProjectTab,
)



class RightPanel(Panel):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.history_tab = HistoryTab(self)
        self.project_tab = ProjectTab(self)
        self.methods_tab = MethodsTab(self)
        self.lca_results_tab = ImpactAssessmentTab(self)

        self.addTab(self.project_tab, 'Project')
        self.addTab(self.methods_tab, 'Impact Categories')
        self.addTab(self.history_tab, 'History')

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
