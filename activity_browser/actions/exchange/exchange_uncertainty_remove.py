from typing import List, Any

from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons
from activity_browser.bwutils import uncertainty


class ExchangeUncertaintyRemove(NewABAction):
    """
    ABAction to clear the uncertainty of one or multiple exchanges.
    """
    icon = qicons.delete
    text = "Remove uncertainty/-ies"

    @staticmethod
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            for key, value in uncertainty.EMPTY_UNCERTAINTY.items():
                exchange[key] = value

            exchange.save()
