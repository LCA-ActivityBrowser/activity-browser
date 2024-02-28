from typing import Union, Callable, List

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application, impact_category_controller
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
        old_cfs = bw.Method(self.method_name).load()

        # get the old_keys to be able to check for duplicates
        if old_cfs:
            old_keys, _ = list(zip(*old_cfs))
        # if no cfs, keys is an empty list
        else:
            old_keys = []

        # use only the keys that don't already exist within the method
        unique_keys = [key for key in self.keys if key not in old_keys]

        # if there are non-unique keys warn the user that these won't be added
        if len(unique_keys) < len(self.keys):
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Duplicate characterization factors",
                "One or more of these elementary flows already exist within this method. Duplicate flows will not be "
                "added"
            )

        # construct new characterization factors from the unique keys
        new_cfs = []
        for key in unique_keys:
            new_cfs.append((key, 0.0))

        # return if there are none
        if not new_cfs: return

        # otherwise instruct the ICController to write the new CF's to the method
        impact_category_controller.write_char_factors(self.method_name, new_cfs, overwrite=False)
