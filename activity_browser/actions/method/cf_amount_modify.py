from typing import List

from activity_browser.brightway import bd
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class CFAmountModify(NewABAction):
    """
    ABAction to modify the amount of a characterization factor within a method. Updates the CF-Tuple's second value
    directly if there's no uncertainty dict. Otherwise, changes the "amount" from the uncertainty dict.
    """
    icon = qicons.edit
    text = "Modify amount"

    @staticmethod
    def run(method_name: tuple, char_factors: List[tuple], amount: float):
        method = bd.Method(method_name)
        method_dict = method.load_dict()
        cf = char_factors[0]

        if isinstance(cf[1], dict):
            method_dict[cf[0]]['amount'] = amount
        else:
            method_dict[cf[0]] = amount

        method.write_dict(method_dict)


