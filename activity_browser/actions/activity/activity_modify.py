from activity_browser.actions.base import ABAction, exception_dialogs
from bw2data import get_activity
from activity_browser.ui.icons import qicons

from .activity_redo_allocation import MultifunctionalProcessRedoAllocation


class ActivityModify(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """

    icon = qicons.edit
    text = "Modify Activity"

    @staticmethod
    @exception_dialogs
    def run(activity_key: tuple, field: str, value: any):
        activity = get_activity(activity_key)

        if field == "default_allocation":
            old_default = activity.get("default_allocation")

        activity[field] = value
        activity.save()

        if field == "default_allocation":
            try:
                MultifunctionalProcessRedoAllocation.run(activity)
            except Exception as e:
                # Rollback
                activity["default_allocation"] = old_default
                activity.save()
                raise e
