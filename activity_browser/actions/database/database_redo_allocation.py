from PySide2 import QtGui

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.logger import log
from activity_browser.mod import bw2data as bd


class DatabaseRedoAllocation(ABAction):
    """
    ABAction to redo the allocation calculation.
    """

    icon = QtGui.QIcon()
    text = "Redo allocation for database"
    tool_tip = "Redo the allocation calculations for this database"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        if bd.databases[db_name].get("backend") == "multifunctional":
            try:
                bd.Database(db_name).process()
                signals.new_statusbar_message.emit(f"Allocation values for database {db_name} updated.")
            except KeyError as exc:
                signals.new_statusbar_message.emit("A property for the allocation calculation was not found!")
                log.error(f"A property for the allocation calculation was not found: {exc}")
            except ZeroDivisionError as exc:
                signals.new_statusbar_message.emit(str(exc))
                log.error(f"Zero division in allocation calculation: {exc}")
