from logging import getLogger

import bw2data as bd
import bw_functional as bf

from activity_browser import signals, bwutils, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class ActivityOpen(ABAction):
    """
    ABAction to open one or more activities.

    This action processes a list of activities, validates their types, and opens
    their details in the application's central widget. Unsupported activity types
    are logged as warnings.

    Attributes:
        icon (QIcon): The icon representing this action.
        text (str): The display text for this action.
    """

    icon = qicons.right
    text = "Open activity / activities"

    @staticmethod
    @exception_dialogs
    def run(activities: list[tuple | int | bd.Node]):
        """
        Execute the action to open activities.

        This method refreshes the provided activities, validates their types, and
        opens their details in the "Activity Details" group of the central widget.

        Args:
            activities (list[tuple | int | bd.Node]): A list of activities to process.

        Logs:
            Warning: If an activity type is not supported.
        """
        from activity_browser.layouts import pages

        # Refresh the activity nodes to ensure they are up-to-date
        activities = [bwutils.refresh_node(activity) for activity in activities]
        processes = [bwutils.refresh_node(function["processor"]) for function in activities if isinstance(function, bf.Product)]
        activities = list(set(activities + processes))

        for act in activities:
            # Check if the activity type is supported
            if act.get("type") not in ["process", "nonfunctional", "multifunctional", "processwithreferenceproduct"]:
                log.warning(f"Can't open activity {act.key} - opening type: `{act.get('type')}` not supported")
                continue

            # Create a details page for the activity
            page = pages.ActivityDetailsPage(act)
            central = application.main_window.centralWidget()

            # Add the details page to the "Activity Details" group in the central widget
            central.addToGroup("Activity Details", page)
