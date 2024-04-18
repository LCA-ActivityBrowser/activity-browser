from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser.brightway.bw2data import Method
from ..base import ABAction
from ...ui.icons import qicons


class CFAmountModify(ABAction):
    """
    ABAction to modify the amount of a characterization factor within a method. Updates the CF-Tuple's second value
    directly if there's no uncertainty dict. Otherwise, changes the "amount" from the uncertainty dict.
    """
    icon = qicons.edit
    title = "Modify amount"
    method_name: tuple
    char_factors: List[tuple]
    amount: float

    def __init__(self,
                 method_name: Union[tuple, Callable],
                 char_factors: Union[List[tuple], Callable],
                 amount: Union[float, Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, method_name=method_name, char_factors=char_factors, amount=amount)

    def onTrigger(self, toggled):
        method = Method(self.method_name)
        method_dict = method.load_dict()
        cf = self.char_factors[0]

        if isinstance(cf[1], dict):
            method_dict[cf[0]]['amount'] = self.amount
        else:
            method_dict[cf[0]] = self.amount

        method.write_dict(method_dict)


