from typing import Union, Callable, List, Any

import pandas as pd
from PySide2 import QtCore

from ...bwutils import commontasks
from ..base import ABAction
from ...ui.icons import qicons


class ExchangeCopySDF(ABAction):
    """
    ABAction to copy the exchange information in SDF format to the clipboard.
    """
    icon = qicons.superstructure
    title = "Exchanges for scenario difference file"
    exchanges: List[Any]

    def __init__(self, exchanges: Union[List[Any], Callable], parent: QtCore.QObject):
        super().__init__(parent, exchanges=exchanges)

    def onTrigger(self, toggled):
        data = commontasks.get_exchanges_in_scenario_difference_file_notation(self.exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
