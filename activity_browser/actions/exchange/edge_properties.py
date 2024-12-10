from typing import Any, List

from qtpy import QtWidgets, QtGui

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.actions.activity.activity_redo_allocation import MultifunctionalProcessRedoAllocation
from activity_browser.ui.widgets.property_editor import PropertyEditor


class EdgeProperties(ABAction):
    """
    ABAction to open the properties of an activity.
    """
    # No icon for properties
    icon = QtGui.QIcon()
    text = "Edge Properties"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any], read_only: bool, parent: QtWidgets.QWidget):
        if exchanges:
            # Operates on the first, regardless of the selection length
            target = exchanges[0]
            if PropertyEditor.edit_properties(target, read_only, parent):
                target.save()
                # Properties changed, redo allocations, the values might have changed
                MultifunctionalProcessRedoAllocation.run(target.output)
