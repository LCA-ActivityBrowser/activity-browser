from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.bwutils import commontasks
from activity_browser.brightway.bw2data import get_activity, parameters
from activity_browser.brightway.bw2data.parameters import ActivityParameter

from ..parameter.parameter_new_automatic import ParameterNewAutomatic
from ..base import ABAction
from ...ui.icons import qicons


class ExchangeModify(ABAction):
    """
    ABAction to modify an exchange with the supplied data.
    """
    icon = qicons.delete
    title = "Modify exchange"
    exchange: Any
    data_: dict

    def __init__(self, exchange: Union[Any, Callable], data: Union[dict, callable], parent: QtCore.QObject):
        super().__init__(parent, exchange=exchange, data_=data)

    def onTrigger(self, toggled):
        for key, value in self.data_.items():
            self.exchange[key] = value

        self.exchange.save()

        if "formula" in self.data_:
            self.parameterize_exchanges(self.exchange.output.key)

    def parameterize_exchanges(self, key: tuple) -> None:
        """ Used whenever a formula is set on an exchange in an activity.

        If no `ActivityParameter` exists for the key, generate one immediately
        """
        act = get_activity(key)
        group = act._document.id
        if not ActivityParameter.select().where(ActivityParameter.group == group).count():
            ParameterNewAutomatic([key], None).trigger()


        with parameters.db.atomic():
            parameters.remove_exchanges_from_group(group, act)
            parameters.add_exchanges_to_group(group, act)
            ActivityParameter.recalculate_exchanges(group)
