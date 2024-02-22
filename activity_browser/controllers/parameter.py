# -*- coding: utf-8 -*-
from typing import Union

import brightway2 as bw
from bw2data.parameters import *
from PySide2.QtCore import QObject

from activity_browser import signals, application
from activity_browser.bwutils import commontasks as bc


class ParameterController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def add_parameter(self, group: str, data: dict) -> None:
        name = data.get("name")
        amount = str(data.get("amount"))
        p_type = "project"
        if group == "project":
            bw.parameters.new_project_parameters([data])
        elif group in bw.databases:
            bw.parameters.new_database_parameters([data], group)
            p_type = f"database ({group})"
        else:
            bw.parameters.new_activity_parameters([data], group)
            p_type = "activity ({})".format(group)
        signals.added_parameter.emit(name, amount, p_type)

    def auto_add_parameter(self, key: tuple) -> None:
        """ Given the activity key, generate a new row with data from
        the activity and immediately call `new_activity_parameters`.
        """
        act = bw.get_activity(key)
        prep_name = bc.clean_activity_name(act.get("name"))
        group = bc.build_activity_group_name(key, prep_name)
        count = (ActivityParameter.select()
                 .where(ActivityParameter.group == group).count())
        row = {
            "name": "{}_{}".format(prep_name, count + 1),
            "amount": act.get("amount", 1.0),
            "formula": act.get("formula", ""),
            "database": key[0],
            "code": key[1],
        }
        # Save the new parameter immediately.
        bw.parameters.new_activity_parameters([row], group)
        signals.parameters_changed.emit()

    def delete_parameter(self, parameter: ParameterBase) -> None:
        """ Remove the given parameter from the project.

        If there are multiple `ActivityParameters` for a single activity, only
        delete the selected instance, otherwise use `bw.parameters.remove_from_group`
        to clear out the `ParameterizedExchanges` as well.
        """
        if isinstance(parameter, ActivityParameter):
            db = parameter.database
            code = parameter.code
            amount = (ActivityParameter.select()
                      .where((ActivityParameter.database == db) &
                             (ActivityParameter.code == code))
                      .count())

            if amount > 1:
                with bw.parameters.db.atomic():
                    parameter.delete_instance()
            else:
                group = parameter.group
                act = bw.get_activity((db, code))
                bw.parameters.remove_from_group(group, act)
                # Also clear the group if there are no more parameters in it
                exists = (ActivityParameter.select()
                          .where(ActivityParameter.group == group).exists())
                if not exists:
                    with bw.parameters.db.atomic():
                        Group.delete().where(Group.name == group).execute()
        else:
            with bw.parameters.db.atomic():
                parameter.delete_instance()
        # After deleting things, recalculate and signal changes
        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    @staticmethod
    def delete_activity_parameter(key: tuple) -> None:
        """Remove all activity parameters and underlying exchange parameters
        for the given activity key.
        """
        query = (ActivityParameter
                 .select(ActivityParameter.group)
                 .where((ActivityParameter.database == key[0]) &
                        (ActivityParameter.code == key[1]))
                 .tuples())
        if not query.exists():
            return
        groups = set(p[0] for p in query)
        for group in groups:
            bw.parameters.remove_from_group(group, key)
            exists = (ActivityParameter.select()
                      .where(ActivityParameter.group == group)
                      .exists())
            if not exists:
                Group.delete().where(Group.name == group).execute()
        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    def modify_parameter(self, param: ParameterBase, field: str,
                         value: Union[str, float, list]) -> None:
        with bw.parameters.db.atomic() as transaction:
            try:
                if hasattr(param, field):
                    setattr(param, field, value)
                elif field == "order":
                    # Store the given order in the Group used by the parameter
                    if param.group in value:
                        value.remove(param.group)
                    group = Group.get(name=param.group)
                    group.order = value
                    group.expire()
                else:
                    param.data[field] = value
                param.save()
                bw.parameters.recalculate()
            except Exception as e:
                # Anything wrong? Roll the transaction back.
                transaction.rollback()
                raise e
        signals.parameters_changed.emit()

    def rename_parameter(self, parameter: ParameterBase, new_name: str) -> None:
        """
        Rename a parameter
        """
        old_name = parameter.name
        group = self.get_parameter_group(parameter)

        if group == "project":
            bw.parameters.rename_project_parameter(parameter, new_name, True)
        elif group in bw.databases:
            bw.parameters.rename_database_parameter(parameter, new_name, True)
        else:
            bw.parameters.rename_activity_parameter(parameter, new_name, True)

        signals.parameters_changed.emit()
        signals.parameter_renamed.emit(old_name, group, new_name)

    @staticmethod
    def get_parameter_group(parameter: ParameterBase) -> str:
        if isinstance(parameter, ProjectParameter):
            return "project"
        elif isinstance(parameter, DatabaseParameter):
            return parameter.database
        elif isinstance(parameter, ActivityParameter):
            return parameter.group


    @staticmethod
    def modify_parameter_uncertainty(param: ParameterBase, uncertain: dict) -> None:
        unc_fields = {"loc", "scale", "shape", "minimum", "maximum"}
        for k, v in uncertain.items():
            if k in unc_fields and isinstance(v, str):
                # Convert empty values into nan, accepted by stats_arrays
                v = float("nan") if not v else float(v)
            param.data[k] = v
        param.save()
        signals.parameters_changed.emit()

    @staticmethod
    def modify_parameter_pedigree(param: ParameterBase, pedigree: dict) -> None:
        param.data["pedigree"] = pedigree
        param.save()
        signals.parameters_changed.emit()

    @staticmethod
    def clear_broken_activity_parameter(database: str, code: str, group: str) -> None:
        """Take the given information and attempt to remove all of the
        downstream parameter information.
        """
        with bw.parameters.db.atomic() as txn:
            bw.parameters.remove_exchanges_from_group(group, None, False)
            ActivityParameter.delete().where(
                ActivityParameter.database == database,
                ActivityParameter.code == code
            ).execute()
            # Do commit to ensure .exists() call does not include deleted params
            txn.commit()
            exists = (ActivityParameter.select()
                      .where(ActivityParameter.group == group)
                      .exists())
            if not exists:
                # Also clear Group if it is not in use anymore
                Group.delete().where(Group.name == group).execute()


parameter_controller = ParameterController(application)
