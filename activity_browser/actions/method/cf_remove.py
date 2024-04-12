from typing import Union, Callable, List

from PySide2 import QtCore, QtWidgets

from activity_browser import application, ic_controller
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

        method = ic_controller.get(self.method_name)
        method_dict = method.load_dict()

        for cf in self.char_factors:
            method_dict.pop(cf[0])

        method.write_dict(method_dict)
