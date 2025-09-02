from typing import Any, List

from bw2data.parameters import ParameterizedExchange

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ExchangeFormulaRemove(ABAction):
    """
    ABAction to clear the formula's of one or more exchanges.
    """

    icon = qicons.delete
    text = "Clear formula(s)"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            if "formula" not in exchange:
                return

            del exchange["formula"]
            exchange.save()

            ParameterizedExchange.delete().where(ParameterizedExchange.exchange == exchange._document.id).execute()
