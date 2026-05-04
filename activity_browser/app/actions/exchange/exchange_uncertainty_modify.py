from typing import Any, List

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.dialogs import UncertaintyDialog


class ExchangeUncertaintyModify(ABAction):
    """
    ABAction to open the UncertaintyWizard for an exchange
    """

    icon = qicons.edit
    text = "Modify uncertainty"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[bd.Edge], uncertainty_dict: dict = None):

        if uncertainty_dict is None:
            ok, uncertainty_dict = UncertaintyDialog.get_uncertainty_dict(
                parent=app.main_window,
                initial=exchanges[0].uncertainty,
                )
            
            if not ok:
                return
        
        for exchange in exchanges:
            for key, value in uncertainty_dict.items():
                exchange[key] = value
            exchange.save()
