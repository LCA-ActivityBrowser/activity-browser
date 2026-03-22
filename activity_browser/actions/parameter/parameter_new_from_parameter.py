from ast import literal_eval

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import Parameter
from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter, parameters
from activity_browser.ui.icons import qicons

from .parameter_new_automatic import ParameterNewAutomatic


class ParameterNewFromParameter(ABAction):
    """
    ABAction to create a new Parameter from an instantiated Parameter namedtuple
    """

    icon = qicons.add
    text = "New parameter..."

    @staticmethod
    @exception_dialogs
    def run(parameter: Parameter):
        if not isinstance(parameter, Parameter) or parameter.param_type is None:
            raise ValueError("Parameter must be an instance of Parameter")

        if not parameter.name.isidentifier():
            raise ValueError("Parameter name must be a valid Python identifier")

        # select the right group and instruct the controller to create the parameter there
        if parameter.param_type == "project":
            ProjectParameter(
                name=parameter.name,
                formula=parameter.data.get("formula", None),
                amount=parameter.amount,
                data=parameter.data,
            ).save()
        elif parameter.param_type == "database":
            DatabaseParameter(
                database=parameter.group,
                name=parameter.name,
                formula=parameter.data.get("formula", None),
                amount=parameter.amount,
                data=parameter.data,
            ).save()
        elif parameter.param_type == "activity":
            mock = ActivityParameter.get_or_none(group=parameter.group)
            if mock is None:
                ParameterNewAutomatic.run([int(parameter.group)])
                mock = ActivityParameter.get(group=parameter.group)

            ActivityParameter(
                group=parameter.group,
                database=mock.database,
                code=mock.code,
                name=parameter.name,
                formula=parameter.data.get("formula", None),
                amount=parameter.amount,
                data=parameter.data,
            ).save()

        parameters.recalculate()

