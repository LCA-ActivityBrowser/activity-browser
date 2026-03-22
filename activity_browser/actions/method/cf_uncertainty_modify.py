from functools import partial
from typing import List

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards import UncertaintyWizard


class CFUncertaintyModify(ABAction):
    """
    ABAction to launch the UncertaintyWizard for Characterization Factor and handles the output by writing the
    uncertainty data using the ImpactCategoryController to the Characterization Factor in question.
    """

    icon = qicons.edit
    text = "Modify uncertainty"

    @classmethod
    @exception_dialogs
    def run(cls, method_name: tuple, char_factors: List[tuple]):
        wizard = UncertaintyWizard(char_factors[0], application.main_window)
        wizard.complete.connect(partial(cls.wizard_done, method_name))
        wizard.show()

    @staticmethod
    def wizard_done(method_name: tuple, cf: tuple, uncertainty: dict):
        """Update the CF with new uncertainty information, possibly converting
        the second item in the tuple to a dictionary without losing information.
        """
        method = bd.Method(method_name)
        method_dict = {cf[0]: cf[1] for cf in method.load()}

        if isinstance(cf[1], dict):
            cf[1].update(uncertainty)
            method_dict[cf[0]] = cf[1]
        else:
            uncertainty["amount"] = cf[1]
            method_dict[cf[0]] = uncertainty

        method.write(list(method_dict.items()))
