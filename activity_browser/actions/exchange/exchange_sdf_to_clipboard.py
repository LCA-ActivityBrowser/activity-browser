from typing import List

import bw2data as bd
import bw_functional as bf

from activity_browser import bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ExchangeSDFToClipboard(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.superstructure
    text = "SDF to clipboard"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[int | bd.Edge]):
        exchanges = [bwutils.refresh_edge(edge) for edge in exchanges]

        virtual_exchanges = []
        for exchange in exchanges:
            if isinstance(exchange, bf.MFExchange):
                virtual_exchanges += exchange.virtual_edges
            else:
                virtual_exchanges.append(exchange.as_dict())

        df = bwutils.exchanges_to_sdf(virtual_exchanges)
        df.to_clipboard(excel=True, index=False)
