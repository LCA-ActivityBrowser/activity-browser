from typing import Any, List

from qtpy import QtWidgets, QtGui

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.actions.activity.activity_redo_allocation import MultifunctionalProcessRedoAllocation
from activity_browser.mod import bw2data as bd
from activity_browser.ui.widgets.property_editor import PropertyEditor


class NodeProperties(ABAction):
    """
    ABAction to open the properties of the input activity of an exchange.
    """
    # No icon for properties
    icon = QtGui.QIcon()
    text = "Function Properties"

    @staticmethod
    @exception_dialogs
    def run(node_key: tuple, read_only: bool):
        activity = bd.get_activity(node_key)

        if PropertyEditor.edit_properties(activity, read_only, application.main_window):
            activity.save()
            # Properties changed, redo allocations, the values might have changed
            MultifunctionalProcessRedoAllocation.run(activity)
