# -*- coding: utf-8 -*-
import datetime
from typing import Optional, Any
from logging import getLogger

import arrow
import numpy as np
import pandas as pd
from qtpy.QtCore import (QAbstractItemModel, QAbstractTableModel,
                            QModelIndex, QSortFilterProxyModel, Qt, Signal)
from qtpy.QtGui import QBrush

from activity_browser.bwutils import commontasks as bc
from activity_browser.ui.style import style_item

log = getLogger(__name__)


class PandasModel(QAbstractTableModel):
    """Abstract pandas table model adapted from
    https://stackoverflow.com/a/42955764.
    """

    HEADERS = []
    updated = Signal()

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self._dataframe: Optional[pd.DataFrame] = df
        self.filterable_columns = None
        self.different_column_types = {}
        # The list of columns which should be editable by the builtin checkbox editor
        # The value of the dict holds whether the value should also be displayed as text
        self._checkbox_editors: dict[int, tuple[bool, Any, Any]] = {}
        self._columns: list[str] = []

    @property
    def columns(self) -> list[str]:
        if self._dataframe is not None:
            return self._dataframe.columns
        return []

    def rowCount(self, parent=None, *args, **kwargs):
        return 0 if self._dataframe is None else self._dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return 0 if self._dataframe is None else self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        """
        Return value for table index based on a certain DisplayRole enum.

        More on DisplayRole enums: https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum
        """
        if not index.isValid():
            return None
        # instantiate value only in case of DisplayRole or ToolTipRole
        value = None
        tt_date_flag = False  # flag to indicate if value is datetime object and role is ToolTipRole
        if role in [Qt.DisplayRole, Qt.ToolTipRole, "sorting", Qt.EditRole]:
            value = self._dataframe.iat[index.row(), index.column()]
            if isinstance(value, np.float64):
                value = float(value)
            elif isinstance(value, bool):
                value = str(value)
            elif isinstance(value, np.int64):
                value = value.item()
            elif isinstance(value, tuple):
                value = str(value)
            elif isinstance(value, datetime.datetime) and (
                Qt.DisplayRole or Qt.ToolTipRole
            ):
                tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
                time_shift = -tz.utcoffset().total_seconds()
                if role == Qt.ToolTipRole:
                    value = (
                        arrow.get(value)
                        .shift(seconds=time_shift)
                        .format("YYYY-MM-DD HH:mm:ss")
                    )
                    tt_date_flag = True
                elif role == Qt.DisplayRole:
                    value = arrow.get(value).shift(seconds=time_shift).humanize()

        # Handle checkbox editors
        # Checkbox editors can return two values for one cell: the usual display value
        # and a checked / not checked enum. It is useful to return both, when the
        # underlying data is not bool, but text to visualize eventual errors.
        if index.column() in self._checkbox_editors:
            if role == Qt.ItemDataRole.CheckStateRole:
                value = self._dataframe.iat[index.row(), index.column()]
                if isinstance(value, str):
                    log.error(f"Expected bool, received str: {value}!!")
                true_value = self._checkbox_editors[index.column()][1]
                # Convert the data to an appropriate value for the checkbox
                return Qt.CheckState.Checked if value == true_value else Qt.CheckState.Unchecked
            display_value = self._checkbox_editors[index.column()][0]
            if role == Qt.ItemDataRole.DisplayRole and not display_value:
                return None

        # immediately return value in case of DisplayRole or sorting
        if role == Qt.DisplayRole or role == "sorting":
            return value

        # in case of ToolTipRole and date, always show the full date
        if tt_date_flag and role == Qt.ToolTipRole:
            return value

        # in case of ToolTipRole, check whether content fits the cell
        if role == Qt.ToolTipRole:
            parent = self.parent()
            fontMetrics = parent.fontMetrics()

            # get the width of both the cell, and the text
            column_width = parent.columnWidth(index.column())
            text_width = fontMetrics.horizontalAdvance(str(value))
            margin = 10

            # only show tooltip if the text is wider then the cell minus the margin
            if text_width > column_width - margin:
                return value

        if role == Qt.ForegroundRole:
            col_name = self._dataframe.columns[index.column()]
            if col_name not in style_item.brushes:
                col_name = bc.AB_names_to_bw_keys.get(col_name, "")
            return QBrush(
                style_item.brushes.get(col_name, style_item.brushes.get("default"))
            )

        return None

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._dataframe.index[section]
        return None

    def row_data(self, index: int) -> list:
        """Return the row at index as a list."""
        return self._dataframe.iloc[index, :].tolist()

    def to_clipboard(self, rows, columns, include_header: bool = False):
        """Copy the given rows and columns of the dataframe to clipboard"""
        self._dataframe.iloc[rows, columns].to_clipboard(
            index=False, header=include_header
        )

    def to_csv(self, path: str) -> None:
        """Store the dataframe as csv in the given path."""
        self._dataframe.to_csv(path)

    def to_excel(self, path: str) -> None:
        """Store the underlying dataframe as excel in the given path"""
        self._dataframe.to_excel(excel_writer=path)

    def sync(self, *args, **kwargs) -> None:
        """(Re)build the dataframe according to the given arguments."""
        self._dataframe = pd.DataFrame([], columns=self.HEADERS)

    @staticmethod
    def proxy_to_source(proxy: QModelIndex) -> QModelIndex:
        """Step from the QSortFilterProxyModel to the underlying PandasModel."""
        model = proxy.model()
        if not hasattr(model, "mapToSource"):
            return proxy  # Proxy is actually the PandasModel
        return model.mapToSource(proxy)

    def test_query_on_column(
        self, test_type: str, col_data: pd.Series, query
    ) -> pd.Series:
        """Compare query and col_data on test_type, return array with boolean test results."""
        if test_type == "equals":
            return col_data == query
        elif test_type == "does not equal":
            return col_data != query
        elif test_type == "contains":
            return col_data.str.contains(query, regex=False)
        elif test_type == "does not contain":
            return ~col_data.str.contains(query, regex=False)
        elif test_type == "starts with":
            return col_data.str.startswith(query)
        elif test_type == "does not start with":
            return ~col_data.str.startswith(query)
        elif test_type == "ends with":
            return col_data.str.endswith(query)
        elif test_type == "does not end with":
            return ~col_data.str.endswith(query)
        elif test_type == "=":
            return col_data.astype(float) == float(query)
        elif test_type == "!=":
            return col_data.astype(float) != float(query)
        elif test_type == ">=":
            return col_data.astype(float) >= float(query)
        elif test_type == "<=":
            return col_data.astype(float) <= float(query)
        elif test_type == "<= x <=":
            return (float(query[0]) <= col_data.astype(float)) & (
                col_data.astype(float) <= float(query[1])
            )
        else:
            log.warning("unknown filter type >{}<, assuming 'EQUALS'".format(test_type))
            return col_data == query

    def get_filter_mask(self, filters: dict) -> pd.Series:
        """Generate a filter mask of the dataframe based on the filters.

        Returns a pd.Series of boolean results (the mask).
        """
        # get the column name from index
        fc_rev = {v: k for k, v in self.filterable_columns.items()}

        all_mode = filters["mode"]
        all_mask = None
        # iterate over columns
        for col_idx, col_filters in filters.items():
            if col_idx == "mode":
                continue
            col_name = fc_rev[col_idx]
            col_data = self._dataframe[col_name]
            col_mode = col_filters.get("mode", False)
            col_mask = None
            # iterate over filters within column
            for col_filt in col_filters["filters"]:
                if self.different_column_types.get(col_name, False):
                    # this is a 'num' column
                    filt_type, query = col_filt
                    col_data_ = col_data
                else:
                    # this is a 'str' column
                    filt_type, query, case_sensitive = col_filt
                    if case_sensitive:
                        col_data_ = col_data.astype(str)
                    else:
                        col_data_ = col_data.astype(str).str.upper()
                        query = query.upper()

                # run the test
                new_mask = self.test_query_on_column(filt_type, col_data_, query)
                if not any(new_mask):
                    # no matches for this mask, let user know:
                    log.info(
                        "There were no matches for filter: {}: '{}'".format(
                            col_filt[0], col_filt[1]
                        )
                    )

                # create or combine new mask within column
                if isinstance(col_mask, pd.Series) and col_mode == "AND":
                    col_mask = col_mask & new_mask
                elif isinstance(col_mask, pd.Series) and col_mode == "OR":
                    col_mask = col_mask + new_mask
                else:
                    col_mask = new_mask

            # create or combine new mask on columns
            if isinstance(all_mask, pd.Series) and all_mode == "AND":
                all_mask = all_mask & col_mask
            elif isinstance(all_mask, pd.Series) and all_mode == "OR":
                all_mask = all_mask + col_mask
            else:
                all_mask = col_mask
        return all_mask

    def set_read_only(self, read_only: bool):
        """Interface function, to support editable models"""
        pass

    def is_read_only(self) -> bool:
        """Interface function, to support editable models"""
        return True

    def set_builtin_checkbox_delegate(self, column: int, show_text_value: bool,
                                      true_value: Any = True, false_value: Any = False):
        """
        Enables the builtin checkbox delegate for columns.
        Can be used on bool values only.
        As the underlying data can be bool or string, we provide the values to be
        stored as parameters.
        """
        self._checkbox_editors[column] = (show_text_value, true_value, false_value)

class EditablePandasModel(PandasModel):
    """Allows underlying dataframe to be edited through Delegate classes."""

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(df, parent)
        self._read_only = True
        # The list of columns which should always be read-only
        self._read_only_columns: list[int] = []

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Returns ItemIsEditable flag only if the model is not read only
        This prevents editing of data on QAbstractTableModel level.
        """
        if index.isValid():
            result = super().flags(index)
            if not self._read_only and not index.column() in self._read_only_columns:
                result |= Qt.ItemIsEditable
                # Qt.ItemIsUserCheckable is also editable, it allows the clicking
                # of the checkbox
                if index.column() in self._checkbox_editors:
                    result |= Qt.ItemIsUserCheckable
            return result
        return Qt.ItemFlag.NoItemFlags

    def prepare_set_value(self, index: QModelIndex, value: Any,
                          role: int = Qt.EditRole) -> tuple[Any, bool]:
        check_ok = False
        if index.isValid():
            if role == Qt.CheckStateRole and index.column() in self._checkbox_editors:
                true_value = self._checkbox_editors[index.column()][1]
                false_value = self._checkbox_editors[index.column()][2]
                value = true_value if value == Qt.CheckState.Checked else false_value
                check_ok = True
        return (value, check_ok)

    def setData(self, index, value, role=Qt.EditRole):
        """Inserts the given validated data into the given index"""
        if index.isValid():
            value, check_ok = self.prepare_set_value(index, value, role)
            if role == Qt.EditRole or check_ok:
                self._dataframe.iat[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [role])
                return True
        return False

    def set_read_only(self, read_only: bool):
        """Allows to set the model to editable"""
        self._read_only = read_only

    def is_read_only(self) -> bool:
        """Returns if the model is editable"""
        return self._read_only

    def insertRows(self, position, rows=1, parent=QModelIndex()):
        """Add new rows to the underlying dataframe"""
        self.beginInsertRows(parent, position, position + rows - 1)
        new_rows = pd.DataFrame(
            [[None] * self.columnCount()] * rows, columns=self._dataframe.columns
        )
        self._dataframe = pd.concat(
            [self._dataframe.iloc[:position], new_rows, self._dataframe.iloc[position:]]
        ).reset_index(drop=True)
        self.endInsertRows()
        return True

    def removeRows(self, position, rows=1, parent=QModelIndex()):
        """Remove rows from the underlying dataframe"""
        self.beginRemoveRows(parent, position, position + rows - 1)
        self._dataframe = self._dataframe.drop(
            self._dataframe.index[position : position + rows]
        ).reset_index(drop=True)
        self.endRemoveRows()
        return True

    def set_readonly_column(self, column: int):
        if column not in self._read_only_columns:
            self._read_only_columns.append(column)


# Take the classes defined above and add the ItemIsDragEnabled flag
class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging."""

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class EditableDragPandasModel(EditablePandasModel):
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class TreeItem(object):
    __slots__ = ["_data", "_parent", "_children"]

    def __init__(self, data: list, parent=None):
        self._data = data
        self._parent = parent
        self._children = []

    @classmethod
    def build_root(cls, cols: list) -> "TreeItem":
        return cls(cols)

    def clear(self) -> None:
        """Use this method to recursively prune a branch from a tree model.
        When called on the root item, removes the entire tree.

        Make sure to only use this in conjunction with model.beginModelReset
        and model.endModelReset to avoid python crashing.
        """
        for c in self._children:
            c.clear()
        self._children = []

    def appendChild(self, item) -> None:
        self._children.append(item)

    def child(self, row: int) -> "TreeItem":
        return self._children[row]

    @property
    def children(self) -> list:
        return self._children

    def childCount(self) -> int:
        return len(self._children)

    def data(self, column: int):
        return self._data[column]

    def parent(self) -> Optional["TreeItem"]:
        return self._parent

    def row(self) -> int:
        return self._parent.children.index(self) if self._parent else 0

    def __repr__(self) -> str:
        return "({})".format(", ".join(str(x) for x in self._data))


class BaseTreeModel(QAbstractItemModel):
    """Base Model used to present data for QTreeView."""

    HEADERS = []
    updated = Signal()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)
        self.root = None
        self._data = {}

    def columnCount(self, parent: QModelIndex = None, *args, **kwargs) -> int:
        return len(self.HEADERS)

    def data(self, index, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            return str(item.data(index.column()))

        if role == Qt.ForegroundRole:
            col_name = self.HEADERS[index.column()]
            return QBrush(
                style_item.brushes.get(col_name, style_item.brushes.get("default"))
            )

    def headerData(self, column, orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.HEADERS[column]
            except IndexError:
                pass
        return None

    def index(self, row: int, column: int, parent: QModelIndex = None, *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent = parent.internalPointer() if parent.isValid() else self.root
        child = parent.child(row)
        if child:
            return self.createIndex(row, column, child)
        else:
            return QModelIndex()

    def iterator(self, item: TreeItem = None):
        """
        An iterator for the TreeModel items, providing an initial object of type
        None returns a series of objects contained in the TreeModel (including the
        root item as the first returned object). Returns a final None type object
        upon termination.
        """
        if item == None:
            return self.root
        if item.childCount() > 0:  # if its not a leaf
            return item.child(0)  # return the first child
        if item == self.root:
            return
        if item.parent().childCount() > item.row() + 1:  # if there's still a sibling
            return item.parent().child(item.row() + 1)
        else:  # look for siblings from previous "generations"
            parent = item.parent()
            while parent != self.root:
                if parent.parent().childCount() > parent.row() + 1:
                    return parent.parent().child(parent.row() + 1)
                parent = parent.parent()
            # if there are no siblings left return None
        return None

    def parent(self, child: QModelIndex = None):
        if not child.isValid():
            return QModelIndex()

        child = child.internalPointer()
        parent = child.parent()
        if parent == self.root:
            return QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent=None, *args, **kwargs):
        if not parent or parent.column() > 0:
            return 0
        parent = parent.internalPointer() if parent.isValid() else self.root
        return parent.childCount()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setup_model_data(self) -> None:
        """Method used to construct the tree of items for the model."""
        raise NotImplementedError

    def sync(self, *args, **kwargs) -> None:
        pass


class ABSortProxyModel(QSortFilterProxyModel):
    """Reimplementation to allow for sorting on the actual data in cells instead of the visible data.

    See this for context: https://github.com/LCA-ActivityBrowser/activity-browser/pull/1151
    """

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Override to sort actual data, expects `left` and `right` are comparable.

        If `left` and `right` are not the same type, we check if numerical and empty string are compared, if that is the
        case, we assume empty string == 0.
        Added this case for: https://github.com/LCA-ActivityBrowser/activity-browser/issues/1215
        """
        left_data = self.sourceModel().data(left, "sorting")
        right_data = self.sourceModel().data(right, "sorting")

        if not left_data and not right_data:
            return True
        if type(left_data) is type(right_data):
            return left_data < right_data

        # comparing Falsys with types
        if (isinstance(left_data, (int, float))
                and not right_data
        ):  # comparing left number with nothing, compare against '0' instead
            return left_data < 0
        if (isinstance(left_data, str)
                and not right_data
        ):  # comparing left str with nothing, compare against "" instead
            return left_data < ""  # note we use '>' instead of '<', content should be above empty fields
        if (isinstance(right_data, (int, float))
                and not left_data
        ):  # comparing right number with nothing, compare against '0' instead
            return 0 < right_data
        if (isinstance(right_data, str)
                and not left_data
        ):  # comparing right str with nothing, compare against "" instead
            return right_data < ""  # note we use '>' instead of '<', content should be above empty fields

        raise ValueError(
            f"Cannot compare {left_data} and {right_data}, incompatible types."
        )
