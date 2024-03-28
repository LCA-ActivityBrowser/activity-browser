from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import  impact_category_controller
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
        char_factor = list(self.char_factors[0])
        if isinstance(char_factor[1], dict):
            char_factor[1]['amount'] = self.amount
        else:
            char_factor[1] = self.amount
        char_factor = tuple(char_factor)

        impact_category_controller.write_char_factors(self.method_name, [char_factor])


