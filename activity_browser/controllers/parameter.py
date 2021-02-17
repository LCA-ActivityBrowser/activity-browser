# -*- coding: utf-8 -*-
from typing import Union

import brightway2 as bw
from bw2data.parameters import ActivityParameter, Group, ParameterBase
from PySide2.QtCore import QObject, Slot
from PySide2.QtWidgets import QInputDialog, QMessageBox

from ..signals import signals


class ParameterController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.parameter_modified.connect(self.modify_parameter)
        signals.rename_parameter.connect(self.rename_parameter)
        signals.delete_parameter.connect(self.delete_parameter)
        signals.parameter_uncertainty_modified.connect(self.modify_parameter_uncertainty)
        signals.parameter_pedigree_modified.connect(self.modify_parameter_pedigree)
        signals.clear_activity_parameter.connect(self.clear_broken_activity_parameter)

    @Slot(object, name="deleteParameter")
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

    @Slot(object, str, object, name="modifyParameter")
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
                # Anything wrong? Roll the transaction back and throw up a
                # warning message.
                transaction.rollback()
                QMessageBox.warning(
                    self.window, "Could not save changes", str(e),
                    QMessageBox.Ok, QMessageBox.Ok
                )
        signals.parameters_changed.emit()

    @Slot(object, str, name="renameParameter")
    def rename_parameter(self, param: ParameterBase, group: str) -> None:
        """Creates an input dialog where users can set a new name for the
        given parameter.

        NOTE: Currently defaults to updating downstream formulas if needed,
        by sub-classing the QInputDialog class it becomes possible to allow
        users to decide if they want to update downstream parameters.
        """
        new_name, ok = QInputDialog.getText(
            self.window, "Rename parameter", "New parameter name:",
        )
        if not ok or not new_name:
            return
        try:
            old_name = param.name
            if group == "project":
                bw.parameters.rename_project_parameter(param, new_name, True)
            elif group in bw.databases:
                bw.parameters.rename_database_parameter(param, new_name, True)
            else:
                bw.parameters.rename_activity_parameter(param, new_name, True)
            signals.parameters_changed.emit()
            signals.parameter_renamed.emit(old_name, group, new_name)
        except Exception as e:
            QMessageBox.warning(
                self.window, "Could not save changes", str(e),
                QMessageBox.Ok, QMessageBox.Ok
            )

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
