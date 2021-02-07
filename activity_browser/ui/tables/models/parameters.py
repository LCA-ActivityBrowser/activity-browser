# -*- coding: utf-8 -*-
import itertools
from typing import Iterable

from asteval import Interpreter
import brightway2 as bw
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PySide2.QtCore import Slot, QModelIndex
from PySide2.QtWidgets import QInputDialog

from activity_browser.bwutils import commontasks as bc, uncertainty as uc
from activity_browser.signals import signals
from ...widgets import simple_warning_box
from ...wizards import UncertaintyWizard
from .base import EditablePandasModel


class BaseParameterModel(EditablePandasModel):
    COLUMNS = []
    UNCERTAINTY = [
        "uncertainty type", "loc", "scale", "shape", "minimum", "maximum"
    ]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.param_col = 0
        self.dataChanged.connect(self.edit_single_parameter)

    def get_parameter(self, proxy: QModelIndex) -> object:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.param_col]

    def get_key(self, *args) -> tuple:
        """ Use this to build a (partial) key for the current index.
        """
        return "", ""

    @classmethod
    def parse_parameter(cls, parameter) -> dict:
        """ Take the given Parameter object and extract data for a single
        row in the table dataframe

        If the parameter has uncertainty data, include this as well.
        """
        row = {key: getattr(parameter, key, "") for key in cls.COLUMNS}
        data = getattr(parameter, "data", {})
        row.update(cls.extract_uncertainty_data(data))
        row["parameter"] = parameter
        return row

    @classmethod
    def columns(cls) -> list:
        """ Combine COLUMNS, UNCERTAINTY and add 'parameter'.
        """
        return cls.COLUMNS + cls.UNCERTAINTY + ["parameter"]

    @classmethod
    def extract_uncertainty_data(cls, data: dict) -> dict:
        """ This helper function can be used to extract specific uncertainty
        columns from the parameter data

        See:
        https://2.docs.brightway.dev/intro.html#storing-uncertain-values
        https://stats-arrays.readthedocs.io/en/latest/#mapping-parameter-array-columns-to-uncertainty-distributions
        """
        row = {key: data.get(key) for key in cls.UNCERTAINTY}
        return row

    @Slot(QModelIndex, name="editSingleParameter")
    def edit_single_parameter(self, proxy: QModelIndex) -> None:
        """ Take the proxy index and update the underlying brightway Parameter.

        TODO: Move this to the parameter controller
        """
        param = self.get_parameter(proxy)
        with bw.parameters.db.atomic() as transaction:
            try:
                field = self._dataframe.columns[proxy.column()]
                if field not in self.COLUMNS:
                    # Must store value inside 'data' field.
                    param.data[field] = proxy.data()
                else:
                    setattr(param, field, proxy.data())
                param.save()
                # Saving the parameter expires the related group, so recalculate.
                bw.parameters.recalculate()
                signals.parameters_changed.emit()
            except Exception as e:
                # Anything wrong? Roll the transaction back, rebuild the table
                # and throw up a warning message.
                transaction.rollback()
                simple_warning_box(self, "Could not save changes", str(e))
                self.sync()

    def handle_parameter_rename(self, proxy: QModelIndex) -> None:
        """ Creates an input dialog where users can set a new name for the
        selected parameter.

        NOTE: Currently defaults to updating downstream formulas if needed,
        by sub-classing the QInputDialog class it becomes possible to allow
        users to decide if they want to update downstream parameters.
        """
        new_name, ok = QInputDialog.getText(
            self.parent(), "Rename parameter", "New parameter name:",
        )
        if ok and new_name:
            try:
                self.rename_parameter(proxy, new_name)
                signals.parameters_changed.emit()
            except Exception as e:
                simple_warning_box(self, "Could not save changes", str(e))
                self.sync()

    def delete_parameter(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        with bw.parameters.db.atomic():
            param.delete_instance()
        signals.parameters_changed.emit()

    @Slot(name="modifyParameterUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        wizard = UncertaintyWizard(param, self)
        wizard.show()

    @Slot(name="unsetParameterUncertainty")
    def remove_uncertainty(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        signals.parameter_uncertainty_modified.emit(param, uc.EMPTY_UNCERTAINTY)


class ProjectParameterModel(BaseParameterModel):
    COLUMNS = ["name", "amount", "formula"]

    def sync(self) -> None:
        data = [
            self.parse_parameter(p) for p in ProjectParameter.select()
        ]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.refresh_model()

    def add_parameter(self) -> None:
        """ Build a new parameter and immediately store it.

        TODO: Move this to parameter controller.
        """
        counter = (ProjectParameter.select().count() +
                   DatabaseParameter.select().count())
        try:
            bw.parameters.new_project_parameters([
                {"name": "param_{}".format(counter + 1), "amount": 1.0}
            ], False)
            signals.parameters_changed.emit()
        except ValueError as e:
            simple_warning_box(self, "Name already in use!", str(e))

    def rename_parameter(self, proxy, new_name: str, update: bool = True) -> None:
        """TODO: Move this to parameter controller."""
        parameter = self.get_parameter(proxy)
        signals.parameter_renamed.emit(parameter.name, "project", new_name)
        bw.parameters.rename_project_parameter(parameter, new_name, update)

    @staticmethod
    def get_usable_parameters() -> Iterable[list]:
        return (
            [k, v, "project"] for k, v in ProjectParameter.static().items()
        )

    @staticmethod
    def get_interpreter() -> Interpreter:
        interpreter = Interpreter()
        interpreter.symtable.update(ProjectParameter.static())
        return interpreter


class DatabaseParameterModel(BaseParameterModel):
    COLUMNS = ["name", "amount", "formula", "database"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_col = 0

    def sync(self) -> None:
        data = [
            self.parse_parameter(p) for p in DatabaseParameter.select()
        ]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        self.db_col = self._dataframe.columns.get_loc("database")
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.refresh_model()

    def get_key(self, proxy: QModelIndex = None) -> tuple:
        return self.get_database(proxy), ""

    def add_parameter(self) -> None:
        """ Add a new database parameter to the dataframe

        TODO: Move this to parameter controller.
        """
        counter = (ProjectParameter.select().count() +
                   DatabaseParameter.select().count())
        database = next(iter(bw.databases))
        try:
            bw.parameters.new_database_parameters([
                {"name": "param_{}".format(counter + 1), "amount": 1.0}
            ], database, False)
            signals.parameters_changed.emit()
        except ValueError as e:
            simple_warning_box(self, "Name already in use!", str(e))

    def rename_parameter(self, proxy, new_name: str, update: bool = True) -> None:
        """TODO: Move this to parameter controller."""
        parameter = self.get_parameter(proxy)
        signals.parameter_renamed.emit(parameter.name, parameter.database, new_name)
        bw.parameters.rename_database_parameter(parameter, new_name, update)

    @staticmethod
    def get_usable_parameters():
        """ Include the project parameters, and generate database parameters.
        """
        project = ProjectParameterModel.get_usable_parameters()
        database = (
            [p.name, p.amount, "database ({})".format(p.database)]
            for p in DatabaseParameter.select()
        )
        return itertools.chain(project, database)

    def get_database(self, proxy: QModelIndex = None) -> str:
        """ Return the database name of the parameter currently selected.
        """
        idx = self.proxy_to_source(proxy or self.parent().currentIndex())
        return self._dataframe.iat[idx.row(), self.db_col]

    def get_interpreter(self) -> Interpreter:
        """ Take the interpreter from the ProjectParameterTable and add
        (potentially overwriting) all database symbols for the selected index.
        """
        interpreter = ProjectParameterModel.get_interpreter()
        db_name = self.get_database()
        interpreter.symtable.update(DatabaseParameter.static(db_name))
        return interpreter


class ActivityParameterModel(BaseParameterModel):
    COLUMNS = [
        "name", "amount", "formula", "product", "activity", "location",
        "group", "order", "key"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.group_col = 0
        self.key_col = 0
        self.order_col = 0
        signals.add_activity_parameter.connect(self.add_parameter)

    def sync(self) -> None:
        """ Build a dataframe using the ActivityParameters set in brightway
        """
        generate = (
            self.parse_parameter(p)
            for p in (ActivityParameter
                      .select(ActivityParameter, Group.order)
                      .join(Group, on=(ActivityParameter.group == Group.name))
                      .namedtuples())
        )
        data = [x for x in generate if "key" in x]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        # Convert the 'order' column from list into string
        self._dataframe["order"] = self._dataframe["order"].apply(", ".join)
        self.group_col = self._dataframe.columns.get_loc("group")
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.key_col = self._dataframe.columns.get_loc("key")
        self.order_col = self._dataframe.columns.get_loc("order")
        self.refresh_model()

    @classmethod
    def parse_parameter(cls, parameter) -> dict:
        """ Override the base method to add more steps.
        """
        row = super().parse_parameter(parameter)
        # Combine the 'database' and 'code' fields of the parameter into a 'key'
        row["key"] = (parameter.database, parameter.code)
        try:
            act = bw.get_activity(row["key"])
        except:
            # Can occur if an activity parameter exists for a removed activity.
            print("Activity {} no longer exists, removing parameter.".format(row["key"]))
            signals.clear_activity_parameter.emit(
                parameter.database, parameter.code, parameter.group
            )
            return {}
        row["product"] = act.get("reference product") or act.get("name")
        row["activity"] = act.get("name")
        row["location"] = act.get("location", "unknown")
        # Replace the namedtuple with the actual ActivityParameter
        row["parameter"] = ActivityParameter.get_by_id(parameter.id)
        return row

    def add_parameters(self, keys: Iterable[tuple]) -> None:
        # Block signals from `signals` while iterating through dropped keys.
        signals.blockSignals(True)
        for key in keys:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                simple_warning_box(
                    self, "Not allowed",
                    "Activity must be 'process' type, '{}' is type '{}'.".format(
                        act.get("name"), act.get("type")
                    )
                )
                continue
            self.add_parameter(key)
        signals.blockSignals(False)
        signals.parameters_changed.emit()

    @staticmethod
    @Slot(tuple, name="addActivityParameter")
    def add_parameter(key: tuple) -> None:
        """ Given the activity key, generate a new row with data from
        the activity and immediately call `new_activity_parameters`.

        TODO: Move to parameter controller.
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

    def rename_parameter(self, proxy, new_name: str, update: bool = True) -> None:
        """TODO: Move to parameter controller."""
        parameter = self.get_parameter(proxy)
        signals.parameter_renamed.emit(parameter.name, parameter.group, new_name)
        bw.parameters.rename_activity_parameter(parameter, new_name, update)

    def store_group_order(self, proxy) -> None:
        """ Store the given order in the Group used by the parameter linked
        in the proxy.

        TODO: Move partially to parameter controller.
        """
        param = self.get_parameter(proxy)
        order = proxy.data()
        if param.group in order:
            order.remove(param.group)
        group = Group.get(name=param.group)
        group.order = order
        group.expire()

    @Slot()
    def delete_parameter(self, proxy) -> None:
        """ Override the base method to include additional logic.

        If there are multiple `ActivityParameters` for a single activity, only
        delete the selected instance, otherwise use `bw.parameters.remove_from_group`
        to clear out the `ParameterizedExchanges` as well.

        TODO: Move to parameter controller.
        """
        key = self.get_key(proxy)
        query = (ActivityParameter.select()
                 .where(ActivityParameter.database == key[0],
                        ActivityParameter.code == key[1]))

        if query.count() > 1:
            super().delete_parameter(proxy)
        else:
            act = bw.get_activity(key)
            group = self.get_group(proxy)
            bw.parameters.remove_from_group(group, act)
            # Also clear the group if there are no more parameters in it
            exists = (ActivityParameter.select()
                      .where(ActivityParameter.group == group).exists())
            if not exists:
                with bw.parameters.db.atomic():
                    Group.delete().where(Group.name == group).execute()

        bw.parameters.recalculate()
        signals.parameters_changed.emit()

    def get_activity_groups(self, proxy, ignore_groups: list = None) -> Iterable[str]:
        """ Helper method to look into the Group and determine which if any
        other groups the current activity can depend on
        """
        db = self.get_key(proxy)[0]
        ignore_groups = ignore_groups or []
        return (
            param.group for param in (ActivityParameter
                                      .select(ActivityParameter.group)
                                      .where(ActivityParameter.database == db)
                                      .distinct())
            if param.group not in ignore_groups
        )

    @staticmethod
    def get_usable_parameters():
        """ Include all types of parameters.

        NOTE: This method does not take into account which formula is being
        edited, and therefore does not restrict which database or activity
        parameters are returned.
        """
        database = DatabaseParameterModel.get_usable_parameters()
        activity = (
            [p.name, p.amount, "activity ({})".format(p.group)]
            for p in ActivityParameter.select()
        )
        return itertools.chain(database, activity)

    def get_group(self, proxy: QModelIndex = None) -> str:
        """ Retrieve the group of the activity currently selected.
        """
        proxy = proxy or self.parent().currentIndex()
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.group_col]

    def get_interpreter(self) -> Interpreter:
        interpreter = Interpreter()
        group = self.get_group(self.parent().currentIndex())
        interpreter.symtable.update(ActivityParameter.static(group, full=True))
        return interpreter

    def get_key(self, proxy: QModelIndex) -> tuple:
        index = self.proxy_to_source(proxy)
        return self._dataframe.iat[index.row(), self.key_col]

    def edit_single_parameter(self, proxy: QModelIndex) -> None:
        """ Override the base method because `order` is stored in Group,
        not in Activity.
        """
        field = self._dataframe.columns[proxy.column()]
        if field == "order":
            self.store_group_order(proxy)
            bw.parameters.recalculate()
            signals.parameters_changed.emit()
        else:
            super().edit_single_parameter(proxy)
