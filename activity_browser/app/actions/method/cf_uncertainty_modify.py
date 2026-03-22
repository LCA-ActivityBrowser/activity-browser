from functools import partial
from typing import List

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.dialogs import UncertaintyDialog


class CFUncertaintyModify(ABAction):
    """
    ABAction to launch the UncertaintyDialog for Characterization Factor and handles the output by writing the
    uncertainty data using the ImpactCategoryController to the Characterization Factor in question.
    """

    icon = qicons.edit
    text = "Modify uncertainty"

    @classmethod
    @exception_dialogs
    def run(cls, method_name: tuple, char_factors: List[tuple], uncertainty_dict: dict = None):

        if uncertainty_dict is None:
            initial = char_factors[0][1]
            initial = initial if isinstance(initial, dict) else {}

            ok, uncertainty_dict = UncertaintyDialog.get_uncertainty_dict(
                parent=app.main_window,
                initial=initial,
                )

            if not ok:
                return
        
        method = bd.Method(method_name)
        method_dict = {cf[0]: cf[1] for cf in method.load()}

        for cf in char_factors:
            if isinstance(cf[1], dict):
                cf[1].update(uncertainty_dict)
                method_dict[cf[0]] = cf[1]
            else:
                uncertainty_dict["amount"] = cf[1]
                method_dict[cf[0]] = uncertainty_dict
        
        method.write(list(method_dict.items()))
