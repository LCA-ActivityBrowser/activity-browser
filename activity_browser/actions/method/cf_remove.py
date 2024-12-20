from typing import List

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CFRemove(ABAction):
    """
    ABAction to remove one or more Characterization Factors from a method. First ask for confirmation and return if the
    user cancels. Otherwise instruct the ImpactCategoryController to remove the selected Characterization Factors.
    """

    icon = qicons.delete
    text = "Remove CF('s)"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple, char_factors: List[tuple]):
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(
            application.main_window,
            "Deleting Characterization Factors",
            f"Are you sure you want to delete {len(char_factors)} CF('s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No:
            return

        method = bd.Method(method_name)
        method_dict = {cf[0]: cf[1] for cf in method.load()}

        for cf in char_factors:
            method_dict.pop(cf[0])

        method.write(list(method_dict.items()))
