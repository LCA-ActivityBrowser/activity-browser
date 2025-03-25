from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CFAmountModify(ABAction):
    """
    ABAction to modify the amount of a characterization factor within a method. Updates the CF-Tuple's second value
    directly if there's no uncertainty dict. Otherwise, changes the "amount" from the uncertainty dict.
    """

    icon = qicons.edit
    text = "Modify amount"

    @staticmethod
    @exception_dialogs
    def run(method: tuple | bd.Method, key: int | tuple, amount: float):
        if isinstance(method, bd.Method):
            method = method.name

        method = bd.Method(method)
        method_dict = {cf[0]: cf[1] for cf in method.load()}

        if isinstance(method_dict[key], dict):
            method_dict[key]["amount"] = amount
        else:
            method_dict[key] = amount

        method.write(list(method_dict.items()))
