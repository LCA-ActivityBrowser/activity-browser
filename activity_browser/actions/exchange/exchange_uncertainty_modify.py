from typing import Any, List

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.dialogs import UncertaintyDialog

class ExchangeUncertaintyModify(ABAction):
    """
    ABAction to open the UncertaintyWizard for an exchange
    """

    icon = qicons.edit
    text = "Modify uncertainty"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        
        ok, array = UncertaintyDialog.get_uncertainty(
            parent=application.main_window,
            initial=exchanges[0].get("uncertainty", {})
            )
        
        if not ok:
            return
