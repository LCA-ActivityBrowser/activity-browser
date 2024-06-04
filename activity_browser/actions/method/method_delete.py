from typing import List

from PySide2 import QtWidgets

from activity_browser import application, log
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class MethodDelete(ABAction):
    """
    ABAction to remove one or multiple methods. First check whether the method is a node or leaf. If it's a node, also
    include all underlying methods. Ask the user for confirmation, and return if canceled. Otherwise, remove all found
    methods.
    """
    icon = qicons.delete
    text = "Delete Impact Category"

    @staticmethod
    @exception_dialogs
    def run(methods: List[tuple], level: str):
        # this action can handle only one selected method for now
        selected_method = methods[0]

        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for deletion
        if level is not None and level != 'leaf':
            all_methods = [bd.Method(method) for method in bd.methods if set(selected_method).issubset(method)]
        else:
            all_methods = [bd.Method(selected_method)]

        # warn the user about the pending deletion
        warning = QtWidgets.QMessageBox.warning(application.main_window,
                                                "Deleting Method",
                                                f"Are you sure you want to delete this method and possible underlying "
                                                f"methods?\n\n{selected_method}",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.No
                                                )
        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        # instruct the controller to delete the selected methods
        for method in all_methods:
            method.deregister()
            log.info(f"Deleted method {method.name}")
