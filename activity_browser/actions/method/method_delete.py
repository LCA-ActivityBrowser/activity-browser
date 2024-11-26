from typing import List
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


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
    def run(methods: List[tuple]):
        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for deletion
        all_methods = [bd.Method(method) for method in methods]

        if len(all_methods) == 1:
            warning_text = f"Are you sure you want to delete this method?\n\n{methods[0]}"
        else:
            warning_text = f"Are you sure you want to delete {len(all_methods)} methods?"

        # warn the user about the pending deletion
        warning = QtWidgets.QMessageBox.warning(
            application.main_window,
            "Deleting Method",
            warning_text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No:
            return

        # instruct the controller to delete the selected methods
        for method in all_methods:
            method.deregister()
            log.info(f"Deleted method {method.name}")
