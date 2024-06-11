from typing import List

from activity_browser import application, log
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets import TupleNameDialog


class MethodDuplicate(ABAction):
    """
    ABAction to duplicate a method, or node with all underlying methods to a new name specified by the user.
    """

    icon = qicons.copy
    text = "Duplicate Impact Category"

    @staticmethod
    @exception_dialogs
    def run(methods: List[tuple], level: str):
        # this action can handle only one selected method for now
        selected_method = methods[0]

        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for duplication
        if level is not None and level != "leaf":
            all_methods = [
                bd.Method(method)
                for method in bd.methods
                if set(selected_method).issubset(method)
            ]
        else:
            all_methods = [bd.Method(selected_method)]

        # retrieve the new name(s) from the user and return if canceled
        dialog = TupleNameDialog.get_combined_name(
            application.main_window,
            "Impact category name",
            "Combined name:",
            selected_method,
            " - Copy",
        )
        if dialog.exec_() != TupleNameDialog.Accepted:
            return

        # for each method to be duplicated, construct a new location
        location = dialog.result_tuple
        new_names = [location + method.name[len(location) :] for method in all_methods]

        # instruct the ImpactCategoryController to duplicate the methods to the new locations
        for method, new_name in zip(all_methods, new_names):
            if new_name in methods:
                raise Exception("New method name already in use")
            method.copy(new_name)
            log.info(f"Copied method {method.name} into {new_name}")
