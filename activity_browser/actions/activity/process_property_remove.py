from logging import getLogger

from activity_browser import bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Process
from bw2data import databases

log = getLogger(__name__)


class ProcessPropertyRemove(ABAction):
    """
    Remove a specified property from a process and its associated products.

    This method refreshes the given process, validates its type, and checks if the specified
    property exists. If the property is an allocation property, it resets the allocation to
    the database's default allocation. The property is then removed from all products of the process.

    Args:
        process (tuple | int | Process): The process from which the property will be removed.
            Can be a tuple (key), integer (id), or Process object.
        property_name (str): The name of the property to remove.

    Raises:
        ValueError: If the provided process is not of type Process.

    Logs:
        Warning: If the specified property is not found in the process.
    """

    icon = qicons.delete
    text = "Remove property"

    @staticmethod
    @exception_dialogs
    def run(process: tuple | int | Process, property_name: str):
        process = bwutils.refresh_node(process)
        if not isinstance(process, Process):
            raise ValueError(f"Expected a Process-type activity, got {type(process)} instead")

        allocate = property_name == process.get("allocation")

        if property_name not in process.available_properties():
            log.warning(f"Property '{property_name}' not found in process {process.key}.")
            return

        if allocate:
            process["allocation"] = databases[process["database"]].get("default_allocation", "equal")
            process.save()

        # Remove the property from all products of the process
        for product in process.products():
            if property_name not in product.get("properties", {}):
                continue

            del product["properties"][property_name]
            product.save()

