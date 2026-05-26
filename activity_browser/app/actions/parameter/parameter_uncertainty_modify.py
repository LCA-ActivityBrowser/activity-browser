from typing import Any

import bw2data as bd

from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser import app
from activity_browser.bwutils.commontasks import database_is_locked
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

        read_only = database_is_locked(parameter.database)

        if not uncertainty_dict:
            initial = parameter.dict.copy() if "uncertainty type" in parameter.dict else None

            ok, uncertainty_dict = UncertaintyDialog.get_uncertainty_dict(
                parent=app.main_window,
                initial=initial,
                read_only=read_only,
                )
        
            if not ok:
                return
        elif read_only:
            return

        parameter.data.update(uncertainty_dict)
        parameter.save()
        bd.parameters.recalculate()
