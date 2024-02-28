from typing import Union, Callable, List, Optional

import brightway2 as bw
from PySide2 import QtCore

from activity_browser import application, impact_category_controller
from activity_browser.ui.widgets import TupleNameDialog
from ..base import ABAction
from ...ui.icons import qicons


class MethodDuplicate(ABAction):
    """
    ABAction to duplicate a method, or node with all underlying methods to a new name specified by the user.
    """
    icon = qicons.copy
    title = "Duplicate Impact Category"
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

        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for duplication
        if self.level is not None and self.level != 'leaf':
            methods = [bw.Method(method) for method in bw.methods if set(selected_method).issubset(method)]
        else:
            methods = [bw.Method(selected_method)]

        # retrieve the new name(s) from the user and return if canceled
        dialog = TupleNameDialog.get_combined_name(
            application.main_window, "Impact category name", "Combined name:", selected_method, " - Copy"
        )
        if dialog.exec_() != TupleNameDialog.Accepted: return

        # for each method to be duplicated, construct a new location
        location = dialog.result_tuple
        new_names = [location + method.name[len(location):] for method in methods]

        # instruct the ImpactCategoryController to duplicate the methods to the new locations
        impact_category_controller.duplicate_methods(methods, new_names)

