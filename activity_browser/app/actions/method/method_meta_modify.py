from loguru import logger

from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons




class MethodMetaModify(ABAction):
    """
    """

    icon = qicons.delete
    text = "Modify Impact Category metadata"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple[str], key: str, value: str):
        if method_name not in bd.methods:
            logger.warning(f"Can't modify metadata for method {method_name} - method not found")
            return

        bd.methods[method_name][key] = value
        bd.methods.flush()
