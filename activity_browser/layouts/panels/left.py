# -*- coding: utf-8 -*-
from ..tabs import HistoryTab, MethodsTab, ProjectTab
from activity_browser.i18n import _

from .panel import ABTab, TabId


class LeftPanel(ABTab):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)

        tabs = (
            (TabId.PROJECT, "Project", ProjectTab(self)),
            (TabId.IMPACT_CATEGORIES, "Impact Categories", MethodsTab(self)),
            (TabId.HISTORY, "History", HistoryTab(self)),
        )
        for tab_id, source_label, tab in tabs:
            self.add_tab(tab, tab_id, _(source_label), aliases=(source_label,))
        # tabs hidden at start
        self.hide_tab(TabId.HISTORY)
