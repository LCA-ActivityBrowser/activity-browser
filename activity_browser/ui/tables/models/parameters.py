# -*- coding: utf-8 -*-
import itertools
from typing import Iterable

from asteval import Interpreter
import brightway2 as bw
import pandas as pd
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PySide2.QtCore import Slot, QModelIndex

from activity_browser.bwutils import uncertainty as uc
from activity_browser.signals import signals
from activity_browser.ui.wizards import UncertaintyWizard
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
        signals.project_selected.connect(self.sync)
        signals.parameters_changed.connect(self.sync)
        signals.added_parameter.connect(self.sync)

    def get_parameter(self, proxy: QModelIndex) -> object:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.param_col]

    def get_key(self, *args) -> tuple:
        """Use this to build a (partial) key for the current index."""
        return "", ""

    def get_group(self, *args) -> str:
        """Retrieve the group of the parameter currently selected."""
        return "project"

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
    def edit_single_parameter(self, index: QModelIndex) -> None:
        """Take the index and update the underlying brightway Parameter."""
        param = self.get_parameter(index)
        field = self._dataframe.columns[index.column()]
        signals.parameter_modified.emit(param, field, index.data())

    @Slot(QModelIndex, name="startRenameParameter")
    def handle_parameter_rename(self, proxy: QModelIndex) -> None:
        group = self.get_group(proxy)
        param = self.get_parameter(proxy)
        signals.rename_parameter.emit(param, group)

    def delete_parameter(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        signals.delete_parameter.emit(param)

    @Slot(name="modifyParameterUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        wizard = UncertaintyWizard(param, self.parent())
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
        self.updated.emit()

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
        self.updated.emit()

    def get_key(self, proxy: QModelIndex = None) -> tuple:
        return self.get_database(proxy), ""

    def get_group(self, proxy: QModelIndex = None) -> str:
        """ Retrieve the group of the activity currently selected.
        """
        return self.get_database(proxy)

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
        self.updated.emit()

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

    @staticmethod
    @Slot(tuple, name="addActivityParameter")
    def add_parameter(key: tuple) -> None:
        signals.add_activity_parameter.emit(key)

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
