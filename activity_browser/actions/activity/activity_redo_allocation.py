from qtpy import QtGui
from logging import getLogger

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)

class MultifunctionalProcessRedoAllocation(ABAction):
    """
    ABAction to redo the allocation calculation for a specific process.
    """

    icon = QtGui.QIcon()
    text = "Redo allocation for multifunctional process"
    tool_tip = "Redo the allocation calculations for this process"

    @staticmethod
    @exception_dialogs
    def run(node: bd.Node):
        if not getattr(node, "multifunctional", None):
            return
        try:
            node.allocate()

            signals.new_statusbar_message.emit(f"Allocation values for process {node} updated.")
        except KeyError as exc:
            signals.new_statusbar_message.emit("A property for the allocation calculation was not found!")
            log.error(f"A property for the allocation calculation was not found: {node}")
            raise exc
        except ZeroDivisionError as exc:
            signals.new_statusbar_message.emit(str(exc))
            log.error(f"Zero division in allocation calculation: {exc}")
            raise exc
