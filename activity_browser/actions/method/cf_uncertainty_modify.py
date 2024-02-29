from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import application, impact_category_controller
from ..base import ABAction
from ...ui.icons import qicons
from ...ui.wizards import UncertaintyWizard


class CFUncertaintyModify(ABAction):
    """
    ABAction to launch the UncertaintyWizard for Characterization Factor and handles the output by writing the
    uncertainty data using the ImpactCategoryController to the Characterization Factor in question.
    """
    icon = qicons.edit
    title = "Modify uncertainty"
    method_name: tuple
    char_factors: List[tuple]
    wizard: UncertaintyWizard

    def __init__(self,
                 method_name: Union[tuple, Callable],
                 char_factors: Union[List[tuple], Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, method_name=method_name, char_factors=char_factors)

    def onTrigger(self, toggled):
        self.wizard = UncertaintyWizard(self.char_factors[0], application.main_window)
        self.wizard.complete.connect(self.wizardDone)
        self.wizard.show()

    def wizardDone(self, cf: tuple, uncertainty: dict):
        """Update the CF with new uncertainty information, possibly converting
        the second item in the tuple to a dictionary without losing information.
        """
        data = [*cf]
        if isinstance(data[1], dict):
            data[1].update(uncertainty)
        else:
            uncertainty["amount"] = data[1]
            data[1] = uncertainty

        impact_category_controller.write_char_factors(self.method_name, [tuple(data)])

