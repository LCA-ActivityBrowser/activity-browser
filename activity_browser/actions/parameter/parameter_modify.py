from logging import getLogger

import bw2data as bd
from bw2data.parameters import ParameterBase, parameters, ActivityParameter, Group, GroupDependency
from peewee import DoesNotExist

from activity_browser.ui.icons import qicons
from activity_browser.bwutils import refresh_parameter, Parameter
from activity_browser.actions.base import ABAction, exception_dialogs

from .parameter_rename import ParameterRename

log = getLogger(__name__)


class ParameterModify(ABAction):
    """
    ABAction to delete an existing parameter.
    """

    icon = qicons.edit
    text = "Modify Parameter"

    @staticmethod
    @exception_dialogs
    def run(parameter: tuple | Parameter | ParameterBase, field: str, value: any):
        parameter = refresh_parameter(parameter)
        param_model = parameter.to_peewee_model()

        if field == "data":
            param_model.data.update(value)
        elif field == "name":
            return ParameterRename.run(parameter, value)
        elif field in dir(param_model):
            setattr(param_model, field, value)
        else:
            param_model.data.update({field: value})

        param_model.save()

        if field in ("amount", "formula"):
            ParameterModify.fix_broken_groups()
            parameters.recalculate()

    @staticmethod
    def fix_broken_groups():
        groups = Group.select().execute()
        for group in groups:
            if group.name == "project" or group.name in bd.databases:
                continue
            try:
                ActivityParameter._static_dependencies(group.name)
            except DoesNotExist:
                log.warning(f"Removing broken parameter group {group.name}")
                GroupDependency.get(GroupDependency.group == group.name).delete_instance()
                group.delete_instance()
