import itertools
from typing import Iterable, Tuple
from logging import getLogger

import pandas as pd
import numpy as np
from asteval import Interpreter
from peewee import DoesNotExist

from qtpy import QtWidgets
from qtpy.QtCore import QModelIndex, Slot

from bw2data.parameters import ActivityParameter, DatabaseParameter, Group, ProjectParameter

from activity_browser import actions, signals, application, bwutils
from activity_browser.mod import bw2data as bd
from activity_browser.ui.wizards import UncertaintyWizard

from .base import BaseTreeModel, EditablePandasModel, TreeItem, PandasModel

log = getLogger(__name__)


class BaseParameterModel(EditablePandasModel):
    COLUMNS = []
    UNCERTAINTY = ["uncertainty type", "loc", "scale", "shape", "minimum", "maximum"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.param_col = 0
        self.comment_col = 0
        self.dataChanged.connect(self.edit_single_parameter)
        self.set_read_only(False)

        signals.project.changed.connect(self.sync)
        signals.parameter.changed.connect(self.sync)
        signals.parameter.recalculated.connect(self.sync)

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
        """Take the given Parameter object and extract data for a single
        row in the table dataframe

        If the parameter has uncertainty data, include this as well.
        """
        row = {key: getattr(parameter, key, "") for key in cls.COLUMNS}
        data = getattr(parameter, "data", {})
        row.update(cls.extract_uncertainty_data(data))
        row["parameter"] = parameter
        row["comment"] = data.get("comment", "")
        return row

    @classmethod
    def columns(cls) -> list:
        """Combine COLUMNS, UNCERTAINTY and add 'parameter'."""
        return cls.COLUMNS + cls.UNCERTAINTY + ["parameter"]

    @classmethod
    def extract_uncertainty_data(cls, data: dict) -> dict:
        """This helper function can be used to extract specific uncertainty
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

        try:
            actions.ParameterModify.run(param, field, index.data())
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Could not save changes",
                str(e),
                QtWidgets.QMessageBox.Ok,
                QtWidgets.QMessageBox.Ok,
            )

    @Slot(QModelIndex, name="startRenameParameter")
    def handle_parameter_rename(self, proxy: QModelIndex) -> None:
        group = self.get_group(proxy)
        param = self.get_parameter(proxy)

        actions.ParameterRename.run(param)

    def delete_parameter(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        actions.ParameterDelete.run(param)

    @Slot(name="modifyParameterUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        wizard = UncertaintyWizard(param, self.parent())
        wizard.show()

    @Slot(name="unsetParameterUncertainty")
    def remove_uncertainty(self, proxy: QModelIndex) -> None:
        param = self.get_parameter(proxy)
        actions.ParameterUncertaintyRemove.run(param)

    def handle_double_click(self, proxy: QModelIndex) -> None:
        column = proxy.column()
        if self._dataframe.columns[column] in BaseParameterModel.UNCERTAINTY:
            self.modify_uncertainty(proxy)
        elif self._dataframe.columns[column] == "name":
            self.handle_parameter_rename(proxy)


class ProjectParameterModel(BaseParameterModel):
    COLUMNS = ["name", "amount", "formula", "comment"]

    def sync(self) -> None:
        data = [self.parse_parameter(p) for p in ProjectParameter.select()]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.comment_col = self._dataframe.columns.get_loc("comment")
        self.updated.emit()

    @staticmethod
    def get_usable_parameters() -> Iterable[list]:
        return ([k, v, "project"] for k, v in ProjectParameter.static().items())

    @staticmethod
    def get_interpreter() -> Interpreter:
        interpreter = Interpreter()
        interpreter.symtable.update(ProjectParameter.static())
        return interpreter


class DatabaseParameterModel(BaseParameterModel):
    COLUMNS = ["name", "amount", "formula", "database", "comment"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_col = 0

    def sync(self) -> None:
        data = [self.parse_parameter(p) for p in DatabaseParameter.select()]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        self.db_col = self._dataframe.columns.get_loc("database")
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.comment_col = self._dataframe.columns.get_loc("comment")
        self.updated.emit()

    def get_key(self, proxy: QModelIndex = None) -> tuple:
        return self.get_database(proxy), ""

    def get_group(self, proxy: QModelIndex = None) -> str:
        """Retrieve the group of the activity currently selected."""
        return self.get_database(proxy)

    @staticmethod
    def get_usable_parameters():
        """Include the project parameters, and generate database parameters."""
        project = ProjectParameterModel.get_usable_parameters()
        database = (
            [p.name, p.amount, "database ({})".format(p.database)]
            for p in DatabaseParameter.select()
        )
        return itertools.chain(project, database)

    def get_database(self, proxy: QModelIndex = None) -> str:
        """Return the database name of the parameter currently selected."""
        idx = self.proxy_to_source(proxy or self.parent().currentIndex())
        return self._dataframe.iat[idx.row(), self.db_col]

    def get_interpreter(self) -> Interpreter:
        """Take the interpreter from the ProjectParameterTable and add
        (potentially overwriting) all database symbols for the selected index.
        """
        interpreter = ProjectParameterModel.get_interpreter()
        db_name = self.get_database()
        interpreter.symtable.update(DatabaseParameter.static(db_name))
        return interpreter


class ActivityParameterModel(BaseParameterModel):
    COLUMNS = [
        "name",
        "amount",
        "formula",
        "product",
        "activity",
        "location",
        "group",
        "order",
        "key",
        "comment",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.group_col = 0
        self.key_col = 0
        self.order_col = 0

    def sync(self) -> None:
        """Build a dataframe using the ActivityParameters set in brightway"""
        generate = (
            self.parse_parameter(p)
            for p in (
                ActivityParameter.select(ActivityParameter, Group.order)
                .join(Group, on=(ActivityParameter.group == Group.name))
                .namedtuples()
            )
        )
        data = [x for x in generate if "key" in x]
        self._dataframe = pd.DataFrame(data, columns=self.columns())
        # Convert the 'order' column from list into string
        self._dataframe["order"] = self._dataframe["order"].apply(", ".join)
        self.group_col = self._dataframe.columns.get_loc("group")
        self.param_col = self._dataframe.columns.get_loc("parameter")
        self.key_col = self._dataframe.columns.get_loc("key")
        self.order_col = self._dataframe.columns.get_loc("order")
        self.comment_col = self._dataframe.columns.get_loc("comment")
        self.updated.emit()

    @classmethod
    def parse_parameter(cls, parameter) -> dict:
        """Override the base method to add more steps."""
        row = super().parse_parameter(parameter)
        # Combine the 'database' and 'code' fields of the parameter into a 'key'
        row["key"] = (parameter.database, parameter.code)
        try:
            act = bd.get_activity(row["key"])
        except:
            # Can occur if an activity parameter exists for a removed activity.
            log.info(
                "Activity {} no longer exists, removing parameter.".format(row["key"])
            )
            actions.ParameterClearBroken.run(parameter)
            return {}
        row["product"] = act.get("reference product") or act.get("name")
        row["activity"] = act.get("name")
        row["location"] = act.get("location", "unknown")
        # Replace the namedtuple with the actual ActivityParameter
        row["parameter"] = ActivityParameter.get_by_id(parameter.id)
        return row

    def get_activity_groups(self, proxy, ignore_groups: list = None) -> Iterable[str]:
        """Helper method to look into the Group and determine which if any
        other groups the current activity can depend on
        """
        db = self.get_key(proxy)[0]
        ignore_groups = ignore_groups or []
        return (
            param.group
            for param in (
                ActivityParameter.select(ActivityParameter.group)
                .where(ActivityParameter.database == db)
                .distinct()
            )
            if param.group not in ignore_groups
        )

    @staticmethod
    def get_usable_parameters():
        """Include all types of parameters.

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
        """Retrieve the group of the activity currently selected."""
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


class ParameterItem(TreeItem):
    @classmethod
    def build_header(cls, header: str, parent: TreeItem) -> "ParameterItem":
        item = cls([header, "", "", ""], parent)
        parent.appendChild(item)
        return item

    @classmethod
    def build_item(cls, param, parent: TreeItem) -> "ParameterItem":
        """Depending on the parameter type, the group is changed, defaults to
        'project'.

        For Activity parameters, use a 'header' item as parent, create one
        if it does not exist.
        """
        group = "project"
        if hasattr(param, "code") and hasattr(param, "database"):
            database = "database - {}".format(str(param.database))
            if database not in [x.data(0) for x in parent.children]:
                cls.build_header(database, parent)
            parent = next(x for x in parent.children if x.data(0) == database)
            group = getattr(param, "group")
        elif hasattr(param, "database"):
            group = param.database

        item = cls(
            [
                getattr(param, "name", ""),
                group,
                getattr(
                    param, "amount", 1.0
                ),  # set to 1 instead of 0 as division by 0 causes problems
                getattr(param, "formula", ""),
            ],
            parent,
        )

        # If the variable is found, we're working on an activity parameter
        if "database" in locals():
            cls.build_exchanges(param, item)

        parent.appendChild(item)
        return item

    @classmethod
    def build_exchanges(cls, act_param, parent: TreeItem) -> None:
        """Take the given activity parameter, retrieve the matching activity
        and construct tree-items for each exchange with a `formula` field.
        """
        act = bd.get_activity((act_param.database, act_param.code))

        for exc in [exc for exc in act.exchanges() if "formula" in exc]:
            try:
                act_input = bd.get_activity(exc.input)
                item = cls(
                    [
                        act_input.get("name"),
                        parent.data(1),
                        exc.amount,
                        exc.get("formula"),
                    ],
                    parent,
                )
                parent.appendChild(item)
            except DoesNotExist as e:
                # The exchange is coming from a deleted database, remove it
                log.warning(f"Broken exchange: {exc}, removing.")
                actions.ExchangeDelete.run([exc])


class ParameterTreeModel(BaseTreeModel):
    """
    Ordering and foldouts as follows:
    - Project parameters:
        - All 'root' objects
        - No children
    - Database parameters:
        - All 'root' objects
        - No children
    - Activity parameters:
        - Never root objects.
        - Placed under simple 'database' root objects
        - Exchanges as children
    - Exchange parameters:
        - Never root objects
        - Children of relevant activity parameter
        - No children
    """

    HEADERS = ["Name", "Group", "Amount", "Formula"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = ParameterItem.build_root(self.HEADERS)
        self.setup_model_data()

    def setup_model_data(self) -> None:
        """First construct the root, then process the data."""
        for param in self._data.get("project", []):
            ParameterItem.build_item(param, self.root)
        for param in self._data.get("database", []):
            ParameterItem.build_item(param, self.root)
        for param in self._data.get("activity", []):
            try:
                _ = bd.get_activity((param.database, param.code))
            except:
                continue
            ParameterItem.build_item(param, self.root)

    def sync(self, *args, **kwargs) -> None:
        self.beginResetModel()
        self.root.clear()
        self.endResetModel()
        self._data.update(
            {
                "project": ProjectParameter.select().iterator(),
                "database": DatabaseParameter.select().iterator(),
                "activity": ActivityParameter.select().iterator(),
            }
        )
        self.setup_model_data()
        self.updated.emit()


class ScenarioModel(PandasModel):
    HEADERS = ["Name", "Group", "default"]
    MATCH_COLS = ["Name", "Group"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        signals.project.changed.connect(self.sync)
        signals.parameter.changed.connect(self.rebuild_table)

    @Slot(name="doCleanSync")
    def sync(self, df: pd.DataFrame = None, include_default: bool = True) -> None:
        """Construct the dataframe from the existing parameters, if ``df``
        is given, perform a merge to possibly include additional columns.
        """
        data = [p[:3] for p in bwutils.utils.Parameters.from_bw_parameters()]
        if not isinstance(df, pd.DataFrame):
            self._dataframe = pd.DataFrame(data, columns=self.HEADERS).set_index("Name")
        else:
            required = set(self.MATCH_COLS)
            if not required.issubset(df.columns):
                raise ValueError(
                    "The given dataframe does not contain required columns: {}".format(
                        required.difference(df.columns)
                    )
                )
            assert df.columns.get_loc("Group") == 1
            if isinstance(include_default, bool) and include_default:
                new_df = pd.DataFrame(data, columns=self.HEADERS)
                if "default" in df.columns:
                    df.drop(columns="default", inplace=True)
                self._dataframe = self._perform_merge(new_df, df).set_index("Name")
            else:
                # Now we're gonna need to ensure that the dataframe is of
                # the same size
                assert (
                    len(data) >= df.shape[0]
                ), "Too many parameters found, not possible."
                missing = len(data) - df.shape[0]
                if missing != 0:
                    nan_data = pd.DataFrame(
                        index=pd.RangeIndex(missing), columns=df.columns
                    )
                    df = pd.concat([df, nan_data], ignore_index=True)
                self._dataframe = df.set_index("Name")
        self.updated.emit()

    @classmethod
    def _perform_merge(cls, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        """There are three kinds of actions that can occur: adding new columns,
        updating values in matching columns, and a combination of the two.

        ``left`` dataframe always determines the row-size of the resulting
        dataframe.
        Any `NaN` values in the new columns in ``right`` will be replaced
        with values from the `default` column from ``left``.
        """
        right_columns = right.drop(columns=cls.MATCH_COLS).columns
        matching = right_columns.intersection(left.columns)
        if not matching.empty:
            # Replace values and drop the matching columns
            left[matching] = right[matching]
            right.drop(columns=matching, inplace=True)
            if right.drop(columns=cls.MATCH_COLS).columns.any():
                # Merge the remaining columns
                df = left.merge(right, how="left", on=cls.MATCH_COLS)
            else:
                df = left
        else:
            df = left.merge(right, how="left", on=cls.MATCH_COLS)
        # Now go over the non-standard columns and see if there are any
        # missing values.
        new_cols = df.drop(columns=cls.HEADERS).columns
        missing = new_cols[df[new_cols].isna().any()]
        if not missing.empty:
            idx = missing.append(pd.Index(["default"]))
            df[idx] = df[idx].apply(lambda x: x.fillna(x["default"]), axis=1)
        return df

    @Slot(name="resetDataIndex")
    def rebuild_table(self) -> None:
        """Should be called when the `parameters_changed` signal is emitted.
        Will call sync with a copy of the current dataframe to ensure no
        user-imported data is lost.

        TODO: handle database parameter group changes correctly. Maybe a
         separate signal like rename?
        """
        self.sync(self._dataframe.reset_index())

    @Slot(str, str, str, name="renameParameterIndex")
    def update_param_name(self, old: str, group: str, new: str) -> None:
        """Kind of a cheat, but directly edit the dataframe.index to update
        the table whenever the user renames a parameter.
        """
        new_idx = pd.Index(
            np.where(
                (self._dataframe.index == old) & (self._dataframe["Group"] == group),
                new,
                self._dataframe.index,
            ),
            name=self._dataframe.index.name,
        )
        self._dataframe.index = new_idx
        self.updated.emit()

    def iterate_scenarios(self) -> Iterable[Tuple[str, Iterable]]:
        """Iterates through all of the non-description columns from left to right.

        Returns an iterator of tuples containing the scenario name and a dictionary
        of the parameter names and new amounts.

        TODO: Fix this so it returns the least amount of required information.
        """
        df = self._dataframe.reset_index()
        df = df.set_index(["Group", "Name"])


        return (
            (scenario, df[scenario])
            for scenario in df.columns
        )
