from typing import List
from logging import getLogger

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import signals
from activity_browser.ui import widgets
from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class MethodRename(ABAction):
    """
    ABAction to remove one or multiple methods. First check whether the method is a node or leaf. If it's a node, also
    include all underlying methods. Ask the user for confirmation, and return if canceled. Otherwise, remove all found
    methods.
    """

    text = "Rename Impact Category"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple[str] | list[tuple[str]]):
        # safeguard: only allow renaming one method at a time
        if isinstance(method_name, list):
            if len(method_name) != 1 or not isinstance(method_name[0], tuple):
                raise ValueError("Can only rename one method at a time.")
            method_name = method_name[0]

        method = bd.Method(method_name)

        dialog = widgets.ABListEditDialog(method_name)
        dialog.exec_()

        if not dialog.result() == QtWidgets.QDialog.Accepted:
            return

        new_name = dialog.get_data(as_tuple=True)
        print(new_name)

        if len(new_name) == 0:
            raise RuntimeError("Method name cannot be empty.")

        if new_name in bd.methods:
            raise RuntimeError(f"Method {new_name} already exists.")

        method.copy(new_name).process()

        # this should not happen like this, as the model and therefore signals should be handled declaritavely,
        # but since method renaming is not native to bw2data we have to do it manually here
        signals.method.renamed.emit(method_name, new_name)

        method.deregister()
