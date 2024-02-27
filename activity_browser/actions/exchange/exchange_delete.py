from typing import Union, Callable, List, Any

from PySide2 import QtCore

from activity_browser import exchange_controller
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
        exchange_controller.delete_exchanges(self.exchanges)
