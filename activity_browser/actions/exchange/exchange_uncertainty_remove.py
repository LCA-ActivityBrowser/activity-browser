from typing import Any, List

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import uncertainty
from activity_browser.ui.icons import qicons


class ExchangeUncertaintyRemove(ABAction):
    """
    ABAction to clear the uncertainty of one or multiple exchanges.
    """

    icon = qicons.delete
    text = "Remove uncertainty/-ies"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            for key, value in uncertainty.EMPTY_UNCERTAINTY.items():
                exchange[key] = value

            exchange.save()
