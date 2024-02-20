from activity_browser import signals
from ..ui.icons import qicons
from .base import ABAction


class ActivityOpen(ABAction):
    icon = qicons.right
    title = 'Open ***'
    depends = ["selected_keys"]

    def onTrigger(self, toggled):
        keys = self.parent().selected_keys
        for key in keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)
