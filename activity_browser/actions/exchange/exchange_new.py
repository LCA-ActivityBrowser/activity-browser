from typing import Union, Callable, List, Optional

from PySide2 import QtCore

from ..base import ABAction
from ...ui.icons import qicons
from ...controllers import exchange_controller


class ExchangeNew(ABAction):
    icon = qicons.add
    title = "Add exchanges"
    from_keys: List[tuple]
    to_key: tuple

    def __init__(self,
                 from_keys: Union[List[tuple], Callable],
                 to_key: Union[tuple, Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, from_keys=from_keys, to_key=to_key)

    def onTrigger(self, toggled):
        exchange_controller.add_exchanges(self.from_keys, self.to_key, None)
