from logging import getLogger

from PySide2.QtWidgets import QMessageBox
from bw2data.proxies import ExchangeProxyBase

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.parameters import ActivityParameter
from activity_browser.ui.icons import qicons

from ..parameter.parameter_new_automatic import ParameterNewAutomatic

log = getLogger(__name__)


class ExchangeModify(ABAction):
    """
    ABAction to modify an exchange with the supplied data.
    """

    icon = qicons.delete
    text = "Modify exchange"

    @classmethod
    @exception_dialogs
    def run(cls, exchange: ExchangeProxyBase, data: dict):
        for key, value in data.items():
            if key == "functional" and value:
                if (existing_func_edges := cls.get_functional_edges_to_same(exchange)):
                    log.info(f"Can not set exchange {exchange} to functional, "
                              f"there is already a functional exchange: {existing_func_edges[0]}")
                    QMessageBox.information(
                        application.main_window,
                        f"Cannot change edge to functional",
                        "Products can only be functional in one edge.\n"
                        f"This product is already functional in:\n{existing_func_edges[0]}",
                        QMessageBox.Ok,
                    )
                    return
            exchange[key] = value
        exchange.save()
        if "functional" in data or exchange.output.get("type") == "multifunctional":
            if hasattr(exchange.output, "allocate"):
                exchange.output.allocate()
            exchange.output.save()

        if "formula" in data:
            cls.parameterize_exchanges(exchange.output.key)

    @staticmethod
    def parameterize_exchanges(key: tuple) -> None:
        """Used whenever a formula is set on an exchange in an activity.

        If no `ActivityParameter` exists for the key, generate one immediately
        """
        act = bd.get_activity(key)
        query = (ActivityParameter.database == key[0]) & (
            ActivityParameter.code == key[1]
        )

        if not ActivityParameter.select().where(query).count():
            ParameterNewAutomatic.run([key])

        group = ActivityParameter.get(query).group

        with bd.parameters.db.atomic():
            bd.parameters.remove_exchanges_from_group(group, act)
            bd.parameters.add_exchanges_to_group(group, act)
            ActivityParameter.recalculate_exchanges(group)

    @staticmethod
    def get_functional_edges_to_same(target_exc: ExchangeProxyBase) -> list[ExchangeProxyBase]:
        activity = target_exc.output
        return [exc for exc in activity.exchanges()
                    if exc.input == target_exc.input and exc.get("functional", False)]

