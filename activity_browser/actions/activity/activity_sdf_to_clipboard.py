from typing import List

import bw2data as bd
import bw_functional as bf

from activity_browser import bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivitySDFToClipboard(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.superstructure
    text = "SDF to clipboard"

    @staticmethod
    @exception_dialogs
    def run(activities: List[tuple | int | bd.Node]):
        activities = [bwutils.refresh_node(node) for node in activities]

        exchanges = []
        for activity in activities:
            if isinstance(activity, bf.Product):
                exchanges += activity.virtual_edges
            if isinstance(activity, bf.Process):
                for product in activity.products():
                    exchanges += product.virtual_exchanges
            else:
                exchanges += [exc.to_dict() for exc in activity.exchanges()]

        df = bwutils.exchanges_to_sdf(exchanges)
        df.to_clipboard(excel=True, index=False)
