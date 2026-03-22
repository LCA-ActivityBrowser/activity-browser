from loguru import logger

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd


class CSOpen(ABAction):
    text = "Open"

    @staticmethod
    @exception_dialogs
    def run(cs_names: str | list[str]):
        if isinstance(cs_names, str):
            cs_names = [cs_names]

        for cs_name in cs_names:
            if cs_name not in bd.calculation_setups:
                logger.warning(f"Calculation setup {cs_name} not found")
                continue

            page = app.pages.CalculationSetupPage(cs_name)
            central = app.main_window.centralWidget()

            central.addToGroup("LCA Setup", page)
