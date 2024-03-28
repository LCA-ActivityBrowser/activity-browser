from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import impact_category_controller
from ..base import ABAction
from ...ui.icons import qicons


class CFUncertaintyRemove(ABAction):
    """
    ABAction to remove the uncertainty from one or multiple Characterization Factors.
    """
    icon = qicons.clear
    title = "Remove uncertainty"
    method_name: tuple
    char_factors: List[tuple]

    def __init__(self,
                 method_name: Union[tuple, Callable],
                 char_factors: Union[List[tuple], Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, method_name=method_name, char_factors=char_factors)

    def onTrigger(self, toggled):
        # create a list of CF's of which the uncertainty dict is removed
        cleaned_cfs = []
        for cf in self.char_factors:
            # if there's no uncertainty dict, we may continue
            if not isinstance(cf[1], dict): continue

            # else replace the uncertainty dict with the float found in the amount field of said dict
            cleaned_cfs.append((cf[0], cf[1]['amount']))

        # if the list is empty we don't need to call the controller
        if not cleaned_cfs: return

        # else, instruct the controller to rewrite the characterization factors that had uncertainty dicts.
        impact_category_controller.write_char_factors(self.method_name, cleaned_cfs)


