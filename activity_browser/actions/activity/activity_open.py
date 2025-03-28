from logging import getLogger

import bw2data as bd

from activity_browser import signals, bwutils, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class ActivityOpen(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.right
    text = "Open ***"

    @staticmethod
    @exception_dialogs
    def run(activities: list[tuple | int | bd.Node]):
        from activity_browser.layouts import pages

        activities = [bwutils.refresh_node(activity) for activity in activities]

        for act in activities:
            if act.get("type") not in ["process", "nonfunctional", "multifunctional", "processwithreferenceproduct"]:
                log.warning(f"Can't open activity {act.key} - opening type: `{act.get('type')}` not supported")
                continue

            page = pages.ActivityDetailsPage(act)
            central = application.main_window.centralWidget()

            central.addToGroup("Activity Details", page)
