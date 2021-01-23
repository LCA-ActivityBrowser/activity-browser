# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.parameters import ActivityParameter, Group, ParameterBase
from PySide2.QtCore import QObject, Slot

from ..signals import signals


class ParameterController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.parameter_modified.connect(self.modify_parameter)
        signals.parameter_uncertainty_modified.connect(self.modify_parameter_uncertainty)
        signals.parameter_pedigree_modified.connect(self.modify_parameter_pedigree)
        signals.clear_activity_parameter.connect(self.clear_broken_activity_parameter)

    @staticmethod
    def delete_activity_parameter(key: tuple) -> None:
        """Remove all activity parameters and underlying exchange parameters
        for the given key.
        """
        query = ActivityParameter.select().where(
            ActivityParameter.database == key[0],
            ActivityParameter.code == key[1]
        )
        if not query.exists():
            return
        query = (ActivityParameter
                 .select(ActivityParameter.group)
                 .where(ActivityParameter.database == key[0],
                        ActivityParameter.code == key[1])
                 .tuples())
        groups = set(p[0] for p in query.iterator())
        for group in groups:
            bw.parameters.remove_from_group(group, key)
            exists = (ActivityParameter.select()
                      .where(ActivityParameter.group == group)
                      .exists())
            if not exists:
                Group.delete().where(Group.name == group).execute()
        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    @staticmethod
    @Slot(object, str, object, name="modifyParameter")
    def modify_parameter(param: ParameterBase, field: str, value: object) -> None:
        if hasattr(param, field):
            setattr(param, field, value)
        else:
            param.data[field] = value
        param.save()
        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    @staticmethod
    @Slot(object, object, name="modifyParameterUncertainty")
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
    @Slot(object, object, name="modifyParameterPedigree")
    def modify_parameter_pedigree(param: ParameterBase, pedigree: dict) -> None:
        param.data["pedigree"] = pedigree
        param.save()
        signals.parameters_changed.emit()

    @staticmethod
    @Slot(str, str, str, name="deleteRemnantParameters")
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
