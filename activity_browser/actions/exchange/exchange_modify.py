from typing import Union, Callable, List, Any

from PySide2 import QtCore

from ..base import ABAction
from ...ui.icons import qicons
from ...controllers import exchange_controller


class ExchangeModify(ABAction):
    icon = qicons.delete
    title = "Delete exchange(s)"
    exchange: Any
    data_: dict

    def __init__(self, exchange: Union[Any, Callable], data: Union[dict, callable], parent: QtCore.QObject):
        super().__init__(parent, exchange=exchange, data_=data)

    def onTrigger(self, toggled):
        exchange_controller.edit_exchange(self.exchange, self.data_)
