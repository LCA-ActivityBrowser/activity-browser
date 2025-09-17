from typing import List
from logging import getLogger

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import signals
from activity_browser.ui import widgets
from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class MethodRename(ABAction):
    """
    Renames an existing method in the Brightway2 data structure.

    This method allows renaming a single method by prompting the user for a new name.
    It ensures that only one method is renamed at a time, validates the new name, and
    updates the method in the Brightway2 database.

    Args:
        method_name (tuple[str] | list[tuple[str]]): The name of the method to rename.
            If a list is provided, it must contain exactly one tuple.

    Steps:
    - Ensure only one method is being renamed at a time.
    - Check if the method exists in the Brightway2 database.
    - Open a dialog to prompt the user for the new method name.
    - Validate the new name to ensure it is not empty and does not already exist.
    - Copy the method to the new name and process it.
    - Emit a signal to notify that the method has been renamed.
    - Deregister the old method.

    Raises:
        ValueError: If more than one method is provided for renaming.
        RuntimeError: If the method does not exist, the new name is empty, or the new name already exists.
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
        dialog = widgets.ABListEditDialog(method_name)
        dialog.exec_()

        # if dialog was cancelled, do nothing
        if not dialog.result() == QtWidgets.QDialog.Accepted:
            return

        new_name = dialog.get_data(as_tuple=True)

        # check new name validity
        if len(new_name) == 0:
            raise RuntimeError("Method name cannot be empty.")

        if new_name in bd.methods:
            raise RuntimeError(f"Method {new_name} already exists.")

        # copy method to new name and process
        method.copy(new_name).process()

        # this should not happen like this, as the model and therefore signals should be handled declaritavely,
        # but since method renaming is not native to bw2data we have to do it manually here
        signals.method.renamed.emit(method_name, new_name)

        # deregister old method
        method.deregister()
