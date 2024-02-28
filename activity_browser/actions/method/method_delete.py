from typing import Union, Callable, List, Optional

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application, impact_category_controller
from ..base import ABAction
from ...ui.icons import qicons


class MethodDelete(ABAction):
    """
    ABAction to remove one or multiple methods. First check whether the method is a node or leaf. If it's a node, also
    include all underlying methods. Ask the user for confirmation, and return if canceled. Otherwise, remove all found
    methods.
    """
    icon = qicons.delete
    title = "Delete Impact Category"
    methods: List[tuple]
    level: tuple

    def __init__(self,
                 methods: Union[List[tuple], Callable],
                 level: Optional[Union[tuple, Callable]],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, methods=methods, level=level)

    def onTrigger(self, toggled):
        # this action can handle only one selected method for now
        selected_method = self.methods[0]

        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for deletion
        if self.level is not None and self.level != 'leaf':
            methods = [bw.Method(method) for method in bw.methods if set(selected_method).issubset(method)]
        else:
            methods = [bw.Method(selected_method)]

        # warn the user about the pending deletion
        warning = QtWidgets.QMessageBox.warning(application.main_window,
                                                f"Deleting Method: {selected_method}",
                                                "Are you sure you want to delete this method and possible underlying "
                                                "methods?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.No
                                                )
        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        # instruct the controller to delete the selected methods
        impact_category_controller.delete_methods(methods)
