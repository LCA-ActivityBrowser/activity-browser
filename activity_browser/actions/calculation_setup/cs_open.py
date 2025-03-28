from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSOpen(ABAction):
    text = "Open"

    @staticmethod
    @exception_dialogs
    def run(cs_names: str | list[str]):
        from activity_browser.layouts import pages

        if isinstance(cs_names, str):
            cs_names = [cs_names]

        for cs_name in cs_names:
            if cs_name not in bd.calculation_setups:
                log.warning(f"Calculation setup {cs_name} not found")
                continue

            page = pages.CalculationSetupPage(cs_name)
            central = application.main_window.centralWidget()

            central.addToGroup("LCA Setup", page)
