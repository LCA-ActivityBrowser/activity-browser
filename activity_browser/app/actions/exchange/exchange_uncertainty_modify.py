from typing import Any, List

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.commontasks import database_is_locked
from activity_browser.bwutils.uncertainty import uncertainty_initial_from_flow
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

        read_only = database_is_locked(exchanges[0].output[0])

        if uncertainty_dict is None:
            ok, uncertainty_dict = UncertaintyDialog.get_uncertainty_dict(
                parent=app.main_window,
                initial=uncertainty_initial_from_flow(exchanges[0]),
                read_only=read_only,
                enable_pedigree=True,
            )
            
            if not ok:
                return
        elif read_only:
            return
        
        for exchange in exchanges:
            for key, value in uncertainty_dict.items():
                if key == "pedigree" and value is None:
                    if "pedigree" in exchange:
                        del exchange["pedigree"]
                    continue
                exchange[key] = value
            exchange.save()
