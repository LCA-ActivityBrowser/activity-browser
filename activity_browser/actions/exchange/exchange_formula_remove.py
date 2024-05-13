from typing import List, Any

from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class ExchangeFormulaRemove(NewABAction):
    """
    ABAction to clear the formula's of one or more exchanges.
    """
    icon = qicons.delete
    text = "Clear formula(s)"

    @staticmethod
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            del exchange["formula"]
            exchange.save()
