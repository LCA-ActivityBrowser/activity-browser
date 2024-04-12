from typing import Union, Callable, List

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application, ic_controller
from ..base import ABAction
from ...ui.icons import qicons


class CFNew(ABAction):
    """
    ABAction to add a new characterization flow to a method through one or more elementary-flow keys.
    """
    icon = qicons.add
    title = "New characterization factor"
    method_name: tuple
    keys: List[tuple]

    def __init__(self,
                 method_name: Union[tuple, Callable],
                 keys: Union[List[tuple], Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, method_name=method_name, keys=keys)

    def onTrigger(self, toggled):
        # load old cf's from the Method
        method_dict = ic_controller.get(self.method_name).load_dict()

        # use only the keys that don't already exist within the method
        unique_keys = [key for key in self.keys if key not in method_dict]

        # if there are non-unique keys warn the user that these won't be added
        if len(unique_keys) < len(self.keys):
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Duplicate characterization factors",
                "One or more of these elementary flows already exist within this method. Duplicate flows will not be "
                "added"
            )

        # return if there are no new keys
        if not unique_keys: return

        # add the new keys to the method dictionary
        for key in unique_keys:
            method_dict[key] = 0.0

        # write the updated dict to the method
        ic_controller.get(self.method_name).write_dict(method_dict)
