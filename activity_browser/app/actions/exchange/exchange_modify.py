from bw2data.proxies import ExchangeProxyBase

from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from .exchange_formula_remove import ExchangeFormulaRemove




class ExchangeModify(ABAction):
    """
    ABAction to modify an exchange with the supplied data.
    """

    icon = qicons.delete
    text = "Modify exchange"

    @classmethod
    @exception_dialogs
    def run(cls, exchange: ExchangeProxyBase, data: dict):
        # remove the formula if it is an empty string
        if "formula" in exchange and data.get("formula") == "":
            del data["formula"]
            ExchangeFormulaRemove.run([exchange])

        for key, value in data.items():
            exchange[key] = value

        exchange.save()

        if "formula" in data:
            from activity_browser.bwutils.parameters.formula_exchanges import (
                index_parameterized_flows_for_process,
            )

            index_parameterized_flows_for_process(exchange.output.key)
