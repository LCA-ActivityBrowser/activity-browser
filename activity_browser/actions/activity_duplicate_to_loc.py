from PySide2 import QtWidgets

from activity_browser import signals
from ..ui.icons import qicons
from .base import ABAction


class ActivityDuplicateToLoc(ABAction):
    icon = qicons.copy
    title = 'Duplicate activity to new location'
    depends = ["selected_keys"]
    tool_tip = ('Duplicate this activity to another location.\n'
                'Link the exchanges to a new location if it is available.')

    def onTrigger(self, toggled):
        # TODO: needs a better look because the implementation in the controller is HUGE
        signals.duplicate_activity_new_loc.emit(self.parent().selected_keys())
