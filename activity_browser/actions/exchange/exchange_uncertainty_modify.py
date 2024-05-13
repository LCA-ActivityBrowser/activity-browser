from typing import List, Any

from activity_browser import application
from activity_browser.ui.wizards import UncertaintyWizard
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class ExchangeUncertaintyModify(NewABAction):
    """
    ABAction to open the UncertaintyWizard for an exchange
    """
    icon = qicons.edit
    text = "Modify uncertainty"

    @staticmethod
    def run(exchanges: List[Any]):
        UncertaintyWizard(exchanges[0], application.main_window).show()
