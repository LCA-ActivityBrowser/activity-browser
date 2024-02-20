from PySide2 import QtWidgets

from activity_browser import application
from ..controllers.activity import activity_controller
from ..ui.icons import qicons
from .base import ABAction


class ActivityDuplicate(ABAction):
    icon = qicons.copy
    title = 'Duplicate ***'
    depends = ["selected_keys"]

    def onTrigger(self, toggled):
        keys = self.parent().selected_keys
        activity_controller.duplicate_activities(keys)


