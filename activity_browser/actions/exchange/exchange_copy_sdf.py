from typing import Any, List

import pandas as pd

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import commontasks
from activity_browser.ui.icons import qicons


class ExchangeCopySDF(ABAction):
    """
    ABAction to copy the exchange information in SDF format to the clipboard.
    """

    icon = qicons.superstructure
    text = "Exchanges for scenario difference file"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        data = commontasks.get_exchanges_in_scenario_difference_file_notation(exchanges)
        df = pd.DataFrame(data)
        df.to_clipboard(excel=True, index=False)
