from typing import List

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CFUncertaintyRemove(ABAction):
    """
    ABAction to remove the uncertainty from one or multiple Characterization Factors.
    """

    icon = qicons.clear
    text = "Remove uncertainty"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple, char_factors: List[tuple]):
        # create a list of CF's of which the uncertainty dict is removed
        cleaned_cfs = []
        for cf in char_factors:
            # if there's no uncertainty dict, we may continue
            if not isinstance(cf[1], dict):
                continue

            # else replace the uncertainty dict with the float found in the amount field of said dict
            cleaned_cfs.append((cf[0], cf[1]["amount"]))

        # if the list is empty we can return
        if not cleaned_cfs:
            return

        # else write the cf's to the method
        method = bd.Method(method_name)
        method_dict = {cf[0]: cf[1] for cf in method.load()}

        for cf in cleaned_cfs:
            method_dict[cf[0]] = cf[1]

        method.write(list(method_dict.items()))
