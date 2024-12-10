from logging import getLogger

from qtpy import QtGui

from multifunctional.database import SIMAPRO_ATTRIBUTES

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


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
                db = bd.Database(db_name)
                is_simapro = any(
                    key in db.metadata for key in SIMAPRO_ATTRIBUTES
                ) or db.metadata.get("products_as_process")

                for node in filter(lambda x: x.multifunctional, db):
                    node.allocate(products_as_process=is_simapro)

                signals.new_statusbar_message.emit(f"Allocation values for database {db_name} updated.")
            except KeyError as exc:
                signals.new_statusbar_message.emit("A property for the allocation calculation was not found!")
                log.error(f"A property for the allocation calculation was not found: {exc}")
            except ZeroDivisionError as exc:
                signals.new_statusbar_message.emit(str(exc))
                log.error(f"Zero division in allocation calculation: {exc}")
