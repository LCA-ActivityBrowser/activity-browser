from os import name
from typing import List
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class MethodDelete(ABAction):
    """
    Delete one or more impact assessment methods (impact categories).

    Flow:
    - Confirm with the user.
    - Deregister all selected methods from Brightway.
    - Update all Brightway calculation setups by removing the deleted methods from their
      'ia' list (if present), and serialize the updated setups.

    Notes:
    - Calculation setups can store method identifiers either as tuples (recommended) or
      sometimes as strings for single-level names; the cleanup accounts for both.
    """

    icon = qicons.delete
    text = "Delete Impact Category"

    @staticmethod
    @exception_dialogs
    def run(methods: List[tuple]):
        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for deletion
        all_methods = [bd.Method(method) for method in methods]

        if len(all_methods) == 1:
            warning_text = f"Are you sure you want to delete this method?\n\n{methods[0]}"
        else:
            warning_text = f"Are you sure you want to delete {len(all_methods)} methods?"

        # warn the user about the pending deletion
        warning = QtWidgets.QMessageBox.warning(
            application.main_window,
            "Deleting Method",
            warning_text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No:
            return

        # collect names for calculation setup cleanup
        to_remove = {m.name for m in all_methods}

        # delete all methods by deregistering them
        for method in all_methods:
            method.deregister()
            log.info(f"Deleted method {method.name}")

        # remove deleted methods from all calculation setups
        MethodDelete.remove_methods_from_calculation_setups(to_remove)

    @staticmethod
    def remove_methods_from_calculation_setups(method_names: set[tuple]) -> None:
        """
        Remove given method names from all calculation setups' 'ia' lists and serialize.
        """
        try:
            changed_any = False

            for cs_name, cs in bd.calculation_setups.items():
                ia = cs.get("ia", [])
                
                for name in method_names:
                    if name not in ia:
                        continue  # name not present, skip
                    
                    ia.remove(name)
                    changed_any = True
                    
                    log.info(
                        f"Updated calculation setup '{cs_name}': removed impact category {name}"
                    )

            
            if changed_any:
                bd.calculation_setups.serialize()
        except Exception:
            log.exception("Failed to update calculation setups after method rename")
