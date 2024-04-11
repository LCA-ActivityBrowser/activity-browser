from typing import Union, Callable, List, Any

from PySide2 import QtCore

from activity_browser.bwutils.data import ABExchange
from ..base import ABAction
from ...ui.icons import qicons


class ExchangeDelete(ABAction):
    """
    ABAction to delete one or more exchanges from an activity.
    """
    icon = qicons.delete
    title = "Delete exchange(s)"
    exchanges: List[Any]

    def __init__(self, exchanges: Union[List[Any], Callable], parent: QtCore.QObject):
        super().__init__(parent, exchanges=exchanges)

    def onTrigger(self, toggled):
        for exchange in self.exchanges:
            # get an exchange that sends signals, should become obsolete in due time
            ab_exchange = ABExchange.from_exchange(exchange)
            ab_exchange.delete()
