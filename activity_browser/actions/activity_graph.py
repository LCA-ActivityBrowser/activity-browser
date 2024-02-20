from PySide2 import QtWidgets

from activity_browser import signals
from ..controllers.activity import activity_controller
from ..ui.icons import qicons
from .base import ABAction


class ActivityGraph(ABAction):
    icon = qicons.graph_explorer
    title = "'Open *** in Graph Explorer'"
    depends = ["selected_keys"]

    def onTrigger(self, toggled):
        keys = self.parent().selected_keys()
        for key in keys:
            signals.open_activity_graph_tab.emit(key)
