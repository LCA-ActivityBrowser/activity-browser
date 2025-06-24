import bw2data as bd

from qtpy import QtWidgets, QtGui, QtCore

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Process
from bw2data import databases


class ProcessDefaultPropertyRemove(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.delete
    text = "Remove property"

    @staticmethod
    @exception_dialogs
    def run(process: tuple | int | Process, property_name: str = None):
        process: Process = bwutils.refresh_node(process)
        allocate = property_name == process.get("allocation")

        if property_name not in process.get("default_properties", {}):
            return

        if allocate:
            process["allocation"] = databases[process["database"]].get("default_allocation", "equal")

        del process["default_properties"][property_name]
        process.save()

        for product in process.products():
            if property_name not in product.get("properties", {}):
                continue
            del product["properties"][property_name]
            product.save()

        if allocate:
            process.allocate()
