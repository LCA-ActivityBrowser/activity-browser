from typing import Union, Callable, List, Any

from PySide2 import QtCore

from activity_browser import exchange_controller
from ...controllers.exchange import ABExchange
from ..base import ABAction
from ...ui.icons import qicons


class ExchangeFormulaRemove(ABAction):
    """
    ABAction to clear the formula's of one or more exchanges.
    """
    icon = qicons.delete
    title = "Clear formula(s)"
    exchanges: List[Any]

    def __init__(self, exchanges: Union[List[Any], Callable], parent: QtCore.QObject):
        super().__init__(parent, exchanges=exchanges)

    def onTrigger(self, toggled):
        for exchange in self.exchanges:
            ab_exchange = ABExchange.from_exchange(exchange)
            del ab_exchange["formula"]
            ab_exchange.save()
            # exchange_controller.edit_exchange(exchange, {"formula": None})
