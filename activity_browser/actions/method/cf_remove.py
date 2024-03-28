from typing import Union, Callable, List

from PySide2 import QtCore, QtWidgets

from activity_browser import application, impact_category_controller
from ..base import ABAction
from ...ui.icons import qicons


class CFRemove(ABAction):
    """
    ABAction to remove one or more Characterization Factors from a method. First ask for confirmation and return if the
    user cancels. Otherwise instruct the ImpactCategoryController to remove the selected Characterization Factors.
    """
    icon = qicons.delete
    title = "Remove CF('s)"
    method_name: tuple
    char_factors: List[tuple]

    def __init__(self,
                 method_name: Union[tuple, Callable],
                 char_factors: Union[List[tuple], Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, method_name=method_name, char_factors=char_factors)

    def onTrigger(self, toggled):
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(application.main_window,
                                                "Deleting Characterization Factors",
                                                f"Are you sure you want to delete {len(self.char_factors)} CF('s)?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.No
                                                )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        # else remove the char_factors
        impact_category_controller.delete_char_factors(self.method_name, self.char_factors)


