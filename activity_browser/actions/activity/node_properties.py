from typing import Any, List

from PySide2 import QtWidgets, QtGui

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
    text = "Node Properties"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any], read_only: bool, parent: QtWidgets.QWidget):
        if exchanges:
            # Operates on the first, regardless of the selection length
            target = exchanges[0]
            activity = bd.get_activity(target.input.key)

            if PropertyEditor.edit_properties(activity, read_only, parent):
                activity.save()
                # Properties changed, redo allocations, the values might have changed
                MultifunctionalProcessRedoAllocation.run(activity)
