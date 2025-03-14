# -*- coding: utf-8 -*-
from logging import getLogger

from qtpy.QtCore import Slot

import bw2data as bd

from activity_browser import signals
from activity_browser.bwutils import commontasks as bc
from activity_browser.layouts.pages import ActivityDetailsPage

from ..panels.panel import ABTab

log = getLogger(__name__)


class ActivitiesTab(ABTab):
    """Tab that contains sub-tabs describing activity information."""

    def __init__(self, parent=None):
        super(ActivitiesTab, self).__init__(parent)
        self.setTabsClosable(True)
        self.connect_signals()

    def connect_signals(self):
        signals.unsafe_open_activity_tab.connect(self.unsafe_open_activity_tab)
        signals.safe_open_activity_tab.connect(self.safe_open_activity_tab)
        self.tabCloseRequested.connect(self.close_tab)
        signals.close_activity_tab.connect(self.close_tab_by_tab_name)
        signals.project.changed.connect(self.close_all)

    @Slot(tuple, name="openActivityTab")
    def open_activity_tab(self, key: tuple, read_only: bool = True) -> None:
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            act = bd.get_activity(key)
            new_tab = ActivityDetailsPage(key, self)

            # If this is a new or duplicated activity then we want to exit it
            # ditto check the Technosphere and Biosphere tables
            if not read_only:
                for table in new_tab.grouped_tables:
                    if table.title() in ("Technosphere Flows:", "Biosphere Flows:"):
                        table.setChecked(True)
            self.tabs[key] = new_tab
            tab_index = self.addTab(new_tab, bc.get_activity_name(act, str_length=30))

            new_tab.destroyed.connect(
                lambda: self.tabs.pop(key) if key in self.tabs else None
            )
            new_tab.destroyed.connect(signals.hide_when_empty.emit)
            new_tab.objectNameChanged.connect(
                lambda name: self.setTabText(self.indexOf(new_tab), name)
            )

        self.select_tab(self.tabs[key])
        signals.show_tab.emit("Activity Details")

    @Slot(tuple, name="unsafeOpenActivityTab")
    def unsafe_open_activity_tab(self, key: tuple) -> None:
        self.open_activity_tab(key, False)

    @Slot(tuple, name="safeOpenActivityTab")
    def safe_open_activity_tab(self, key: tuple) -> None:
        self.open_activity_tab(key)

