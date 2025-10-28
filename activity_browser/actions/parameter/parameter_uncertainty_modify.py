from typing import Any

import bw2data as bd

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser import application
from activity_browser.ui.dialogs import UncertaintyDialog
from activity_browser.ui.icons import qicons


class ParameterUncertaintyModify(ABAction):
    """
    ABAction to modify the uncertainty of an existing parameter.
    """

    icon = qicons.edit
    text = "Modify parameter uncertainty"

    @staticmethod
    @exception_dialogs
    def run(parameter: Any, uncertainty_dict: dict=None) -> None:

        if not uncertainty_dict:
            initial = parameter.dict.copy() if "uncertainty type" in parameter.dict else None

            ok, uncertainty_dict = UncertaintyDialog.get_uncertainty_dict(
                parent=application.main_window,
                initial=initial,
                )
        
            if not ok:
                return

        parameter.data.update(uncertainty_dict)
        parameter.save()
        bd.parameters.recalculate()
