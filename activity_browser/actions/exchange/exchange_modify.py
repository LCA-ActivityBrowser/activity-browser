from typing import Any

from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons
from activity_browser.brightway import bd
from activity_browser.brightway.bw2data.parameters import ActivityParameter

from ..parameter.parameter_new_automatic import ParameterNewAutomatic


class ExchangeModify(NewABAction):
    """
    ABAction to modify an exchange with the supplied data.
    """
    icon = qicons.delete
    text = "Modify exchange"

    @classmethod
    def run(cls, exchange: Any, data: dict):
        for key, value in data.items():
            exchange[key] = value

        exchange.save()

        if "formula" in data:
            cls.parameterize_exchanges(exchange.output.key)

    @staticmethod
    def parameterize_exchanges(key: tuple) -> None:
        """ Used whenever a formula is set on an exchange in an activity.

        If no `ActivityParameter` exists for the key, generate one immediately
        """
        act = bd.get_activity(key)
        group = act._document.id
        if not ActivityParameter.select().where(ActivityParameter.group == group).count():
            ParameterNewAutomatic([key], None).trigger()


        with bd.parameters.db.atomic():
            bd.parameters.remove_exchanges_from_group(group, act)
            bd.parameters.add_exchanges_to_group(group, act)
            ActivityParameter.recalculate_exchanges(group)
