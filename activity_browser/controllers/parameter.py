# -*- coding: utf-8 -*-
from typing import List, Optional, Union

import brightway2 as bw
from bw2data.parameters import ActivityParameter, Group, ParameterBase
from PySide2.QtCore import QObject, Slot
from PySide2.QtWidgets import QInputDialog, QMessageBox, QErrorMessage

from activity_browser.bwutils import commontasks as bc
from activity_browser.signals import signals
from activity_browser.ui.wizards import ParameterWizard


class ParameterController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.add_parameter.connect(self.add_parameter)
        signals.add_activity_parameter.connect(self.auto_add_parameter)
        signals.add_activity_parameters.connect(self.multiple_auto_parameters)
        signals.parameter_modified.connect(self.modify_parameter)
        signals.rename_parameter.connect(self.rename_parameter)
        signals.delete_parameter.connect(self.delete_parameter)
        signals.parameter_uncertainty_modified.connect(self.modify_parameter_uncertainty)
        signals.parameter_pedigree_modified.connect(self.modify_parameter_pedigree)
        signals.clear_activity_parameter.connect(self.clear_broken_activity_parameter)

    @Slot(name="createSimpleParameterWizard")
    @Slot(tuple, name="createParameterWizard")
    def add_parameter(self, key: Optional[tuple] = None) -> None:
        key = key or ("", "")
        wizard = ParameterWizard(key, self.window)

        if wizard.exec_() == ParameterWizard.Accepted:
            selection = wizard.selected
            data = wizard.param_data
            name = data.get("name")
            if name[0] in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '#'):
                error = QErrorMessage()
                error.showMessage("<p>Parameter names must not start with a digit, hyphen, or hash character</p>")
                error.exec_()
                return
            amount = str(data.get("amount"))
            p_type = "project"
            if selection == 0:
                bw.parameters.new_project_parameters([data])
            elif selection == 1:
                db = data.pop("database")
                bw.parameters.new_database_parameters([data], db)
                p_type = "database ({})".format(db)
            elif selection == 2:
                group = data.pop("group")
                bw.parameters.new_activity_parameters([data], group)
                p_type = "activity ({})".format(group)
            signals.added_parameter.emit(name, amount, p_type)

    @staticmethod
    @Slot(tuple, name="addActivityParameter")
    def auto_add_parameter(key: tuple) -> None:
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

    @Slot(list, name="addMultipleActivityParams")
    def multiple_auto_parameters(self, keys: List[tuple]) -> None:
        """Block the 'signals' object while iterating through the list of
        keys, adding all of them as activity parameters.
        """
        warning = "Activity must be 'process' type, '{}' is type '{}'."
        signals.blockSignals(True)
        for key in keys:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                issue = warning.format(act.get("name"), act.get("type"))
                QMessageBox.warning(
                    self.window, "Not allowed", issue, QMessageBox.Ok, QMessageBox.Ok
                )
                continue
            self.auto_add_parameter(key)
        signals.blockSignals(False)
        signals.parameters_changed.emit()

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
        text = "Rename parameter '{}' to:".format(param.name)
        new_name, ok = QInputDialog.getText(
            self.window, "Rename parameter", text,
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
