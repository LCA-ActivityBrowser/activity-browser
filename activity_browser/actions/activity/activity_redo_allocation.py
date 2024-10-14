from PySide2 import QtGui

from multifunctional.database import SIMAPRO_ATTRIBUTES

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.logger import log
from activity_browser.mod import bw2data as bd


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
            is_simapro = any(
                key in bd.databases[node['database']] for key in SIMAPRO_ATTRIBUTES
            ) or bd.databases[node['database']].get("products_as_process")

            node.allocate(products_as_process=is_simapro)

            signals.new_statusbar_message.emit(f"Allocation values for process {node} updated.")
        except KeyError as exc:
            signals.new_statusbar_message.emit("A property for the allocation calculation was not found!")
            log.error(f"A property for the allocation calculation was not found: {node}")
        except ZeroDivisionError as exc:
            signals.new_statusbar_message.emit(str(exc))
            log.error(f"Zero division in allocation calculation: {exc}")
