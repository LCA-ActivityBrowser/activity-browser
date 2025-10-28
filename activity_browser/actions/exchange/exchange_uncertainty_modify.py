from typing import Any, List

import bw2data as bd

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
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
    def run(exchanges: List[bd.Edge]):

        ok, uc_dict = UncertaintyDialog.get_uncertainty_dict(
            parent=application.main_window,
            initial=exchanges[0].uncertainty,
            )
        
        if not ok:
            return
        
        for exchange in exchanges:
            for key, value in uc_dict.items():
                exchange[key] = value
            exchange.save()
