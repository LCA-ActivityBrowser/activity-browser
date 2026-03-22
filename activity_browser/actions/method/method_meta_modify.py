from typing import List
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class MethodMetaModify(ABAction):
    """
    """

    icon = qicons.delete
    text = "Modify Impact Category metadata"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple[str], key: str, value: str):
        if method_name not in bd.methods:
            log.warning(f"Can't modify metadata for method {method_name} - method not found")
            return

        bd.methods[method_name][key] = value
        bd.methods.flush()
