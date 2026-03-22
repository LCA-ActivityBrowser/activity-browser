from typing import List
from logging import getLogger

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import application, signals
from activity_browser.ui import widgets
from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class MethodRename(ABAction):
    """
    Rename an existing impact assessment method (impact category).

    Flow:
    - Ensure only one method is selected and it exists.
    - Prompt the user for the new name and validate it.
    - Copy the method to the new name and process it.
    - Update all Brightway calculation setups by replacing the old method in 'ia' lists with
      the new name and serialize the updates.
    - Emit a rename signal and deregister the old method.

    Raises:
    - ValueError: If more than one method is provided for renaming.
    - RuntimeError: If the method does not exist, the new name is empty, or the new name already exists.
    """

    text = "Rename Impact Category"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple[str] | list[tuple[str]]):
        # safeguard: only allow renaming one method at a time
        if isinstance(method_name, list):
            if len(method_name) != 1 or not isinstance(method_name[0], tuple):
                raise ValueError("Can only rename one method at a time.")
            method_name = method_name[0]

        # check if method exists
        if method_name not in bd.methods:
            raise RuntimeError(f"Method {method_name} does not exist.")

        method = bd.Method(method_name)

        # open dialog to get new name
        dialog = widgets.ABListEditDialog(
            method_name,
            title="Rename Impact Category",
            parent=application.main_window,
        )

        # execute the dialog and check for acceptance
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        new_name = dialog.get_data(as_tuple=True)

        # check new name validity
        if new_name == method_name:
            return  # no change

        if len(new_name) == 0:
            raise RuntimeError("Method name cannot be empty.")

        if new_name in bd.methods:
            raise RuntimeError(f"Method {new_name} already exists.")

        # copy method to new name and process
        method.copy(new_name).process()

        # Update any calculation setups that reference this method
        MethodRename.rename_method_in_calculation_setups(method_name, new_name)

        # this should not happen like this, as the model and therefore signals should be handled declaritavely,
        # but since method renaming is not native to bw2data we have to do it manually here
        signals.method.renamed.emit(method_name, new_name)

        # deregister old method
        method.deregister()

    @staticmethod
    def rename_method_in_calculation_setups(old_name: tuple, new_name: tuple) -> None:
        """Replace occurrences of old_name with new_name in all CS 'ia' lists and serialize.

        Handles both tuple and single-string method keys. Best-effort: logs on failure
        without blocking the rename flow.
        """
        try:
            changed_any = False

            for cs_name, cs in bd.calculation_setups.items():
                ia = cs.get("ia", [])
                
                if old_name not in ia:
                    continue

                i = ia.index(old_name)
                ia[i] = new_name

                changed_any = True
                log.info(
                    f"Updated calculation setup '{cs_name}': renamed impact category {old_name} -> {new_name}"
                )
            
            if changed_any:
                bd.calculation_setups.serialize()
        except Exception:
            log.exception("Failed to update calculation setups after method rename")
