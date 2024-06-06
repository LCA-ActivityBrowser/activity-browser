from typing import List, Any

from activity_browser import application
from activity_browser.ui.wizards import UncertaintyWizard
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ExchangeUncertaintyModify(ABAction):
    """
    ABAction to open the UncertaintyWizard for an exchange
    """
    icon = qicons.edit
    text = "Modify uncertainty"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        UncertaintyWizard(exchanges[0], application.main_window).show()
