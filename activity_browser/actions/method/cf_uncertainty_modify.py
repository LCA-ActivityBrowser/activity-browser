from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import application, ic_controller
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
        method = ic_controller.get(self.method_name)
        method_dict = method.load_dict()

        if isinstance(cf[1], dict):
            cf[1].update(uncertainty)
            method_dict[cf[0]] = cf[1]
        else:
            uncertainty["amount"] = cf[1]
            method_dict[cf[0]] = uncertainty

        method.write_dict(method_dict)

