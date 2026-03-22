from typing import List

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CFNew(ABAction):
    """
    ABAction to add a new characterization flow to a method through one or more elementary-flow keys.
    """

    icon = qicons.add
    text = "New characterization factor"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple, keys: List[tuple]):
        # load old cf's from the Method
        method_dict = {cf[0]: cf[1] for cf in bd.Method(method_name).load()}

        # use only the keys that don't already exist within the method
        unique_keys = [key for key in keys if key not in method_dict]

        # if there are non-unique keys warn the user that these won't be added
        if len(unique_keys) < len(keys):
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Duplicate characterization factors",
                "One or more of these elementary flows already exist within this method. Duplicate flows will not be "
                "added",
            )

        # return if there are no new keys
        if not unique_keys:
            return

        # add the new keys to the method dictionary
        for key in unique_keys:
            method_dict[key] = 0.0

        # write the updated dict to the method
        bd.Method(method_name).write(list(method_dict.items()))
