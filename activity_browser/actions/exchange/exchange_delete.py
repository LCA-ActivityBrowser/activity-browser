from typing import Union, Callable, List, Any

from PySide2 import QtCore

from ..base import ABAction
from ...ui.icons import qicons
from ...controllers import exchange_controller


class ExchangeDelete(ABAction):
    icon = qicons.delete
    title = "Delete exchange(s)"
    exchanges: List[Any]

    def __init__(self, exchanges: Union[List[Any], Callable], parent: QtCore.QObject):
        super().__init__(parent, exchanges=exchanges)

    def onTrigger(self, toggled):
        exchange_controller.delete_exchanges(self.exchanges)
