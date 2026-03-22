import os
import datetime
from typing import Optional, Any
from logging import getLogger

import arrow
import numpy as np
import bw2data as bd
import pandas as pd

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal, Slot, SignalInstance
from qtpy.QtWidgets import QSizePolicy, QTableView

from activity_browser.settings import ab_settings
from activity_browser.ui.icons import qicons
from activity_browser.ui import delegates

from .dialogs import FilterManagerDialog, SimpleFilterDialog


log = getLogger(__name__)


class CustomHeader(QtWidgets.QHeaderView):
    """Header which has a filter button on each cell that can trigger a signal.

    Largely based on https://stackoverflow.com/a/30938728
    """

    clicked: SignalInstance = Signal(int, str)

    _x_offset = 0
    _y_offset = (
        0  # This value is calculated later, based on the height of the paint rect
    )
    _width = 18
    _height = 18

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(CustomHeader, self).__init__(orientation, parent)
        self.setSectionsClickable(True)

        self.column_indices = []
        self.has_active_filters = []  # list of column indices that have filters active
        self.event_pos = None

    def paintSection(self, painter, rect, logical_index):
        """Paint the button onto the column header."""
        painter.save()
        super(CustomHeader, self).paintSection(painter, rect, logical_index)
        painter.restore()

        self._y_offset = int(rect.height() - self._width)

        if logical_index in self.column_indices:
            option = QtWidgets.QStyleOptionButton()
            option.rect = QRect(
                rect.x() + self._x_offset,
                rect.y() + self._y_offset,
                self._width,
                self._height,
            )
            option.state = (
                QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_Active
            )

            # put the filter icon onto the label
            if logical_index in self.has_active_filters:
                option.icon = qicons.filter
            else:
                option.icon = qicons.filter_outline
            option.iconSize = QSize(16, 16)

            # set the settings to a PushButton
            self.style().drawControl(QtWidgets.QStyle.CE_PushButton, option, painter)

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index in self.column_indices:
            x = self.sectionPosition(index)
            if (
                x + self._x_offset < event.pos().x() < x + self._x_offset + self._width
                and self._y_offset < event.pos().y() < self._y_offset + self._height
            ):
                # the button is clicked

                # set the position of the lower left point of the filter button to spawn a menu
                pos = QPoint()
                pos.setX(x + self._x_offset + self._width)
                pos.setY(self._y_offset + self._height)
                self.event_pos = pos

                # emit the column index and the button (left/right) pressed
                self.clicked.emit(index, str(event.button()).split(".")[-1])
            else:
                # pass the event to the header (for sorting)
                super(CustomHeader, self).mousePressEvent(event)
        else:
            # pass the event to the header (for sorting)
            super(CustomHeader, self).mousePressEvent(event)
        self.viewport().update()


class PandasModel(QtCore.QAbstractTableModel):
    """Abstract pandas table model adapted from
    https://stackoverflow.com/a/42955764.
    """

    HEADERS = []
    updated: SignalInstance = Signal()

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
    def proxy_to_source(proxy: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """Step from the QSortFilterProxyModel to the underlying PandasModel."""
        model = proxy.model()
        if not hasattr(model, "mapToSource"):
            return proxy  # Proxy is actually the PandasModel
        return model.mapToSource(proxy)

    @staticmethod
    def test_query_on_column(test_type: str, col_data: pd.Series, query) -> bool:
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


class ABSortProxyModel(QtCore.QSortFilterProxyModel):
    """Reimplementation to allow for sorting on the actual data in cells instead of the visible data.

    See this for context: https://github.com/LCA-ActivityBrowser/activity-browser/pull/1151
    """

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
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


class ABMultiColumnSortProxyModel(ABSortProxyModel):
    """Subclass of QSortFilterProxyModel to enable sorting on multiple columns.

    The main purpose of this subclass is to override def filterAcceptsRow().

    Subclass based on various ideas from:
    https://stackoverflow.com/questions/47201539/how-to-filter-multiple-column-in-qtableview
    http://www.dayofthenewdan.com/2013/02/09/Qt_QSortFilterProxyModel.html
    https://gist.github.com/dbridges/4732790
    """

    def __init__(self, parent=None):
        super(ABMultiColumnSortProxyModel, self).__init__(parent)

        # the filter mask, an iterable array with boolean values on whether or not to keep the row
        self.mask = None

        # metric to keep track of successful matches on filter
        self.matches = 0

        # custom filter activation
        self.activate_filter = False

    def set_filters(self, mask) -> None:
        self.mask = mask
        self.matches = 0
        self.activate_filter = True
        self.invalidateFilter()
        self.activate_filter = False
        log.info("{} filter matches found".format(self.matches))

    def clear_filters(self) -> None:
        self.mask = None
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent) -> bool:
        # check if self.activate_filter is enabled, else return True
        if not self.activate_filter:
            return True
        # get the right index from the mask
        matched = self.mask.iloc[row]
        if matched:
            self.matches += 1
        return matched


class ABDataFrameView(QtWidgets.QTableView):
    """Base class for showing pandas dataframe objects as tables."""

    ALL_FILTER = "All Files (*.*)"
    CSV_FILTER = "CSV (*.csv);; All Files (*.*)"
    TSV_FILTER = "TSV (*.tsv);; All Files (*.*)"
    EXCEL_FILTER = "Excel (*.xlsx);; All Files (*.*)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.verticalHeader().setVisible(False)
        # Use a custom ViewOnly delegate by default.
        # Can be overridden table-wide or per column in child classes.
        self.setItemDelegate(delegates.ViewOnlyDelegate(self))

        self.table_name = "LCA results"
        # Initialize attributes which are set during the `sync` step.
        # Creating (and typing) them here allows PyCharm to see them as
        # valid attributes.
        self.model: Optional[PandasModel] = None
        self.proxy_model: Optional[ABSortProxyModel] = None

    def rowCount(self) -> int:
        return 0 if self.model is None else self.model.rowCount()

    @Slot(name="updateProxyModel")
    def update_proxy_model(self) -> None:
        self.proxy_model = ABSortProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

    @Slot(name="exportToClipboard")
    def to_clipboard(self):
        """Copy dataframe to clipboard"""
        rows = list(range(self.model.rowCount()))
        cols = list(range(self.model.columnCount()))
        self.model.to_clipboard(rows, cols, include_header=True)

    def savefilepath(
        self, default_file_name: str, caption: str = None, file_filter: str = None
    ):
        """Construct and return default path where data is stored

        Uses the application directory for AB
        """
        safe_name = bd.utils.safe_filename(default_file_name, add_hash=False)
        caption = caption or "Choose location to save lca results"
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption=caption,
            dir=str(os.path.join(ab_settings.data_dir, safe_name)),
            filter=file_filter or self.ALL_FILTER,
        )
        # getSaveFileName can now weirdly return Path objects.
        return str(filepath) if filepath else filepath

    @Slot(name="exportToCsv")
    def to_csv(self):
        """Save the dataframe data to a CSV file."""
        filepath = self.savefilepath(self.table_name, file_filter=self.CSV_FILTER)
        if filepath:
            if not filepath.endswith(".csv"):
                filepath += ".csv"
            self.model.to_csv(filepath)

    @Slot(name="exportToExcel")
    def to_excel(self, caption: str = None):
        """Save the dataframe data to an excel file."""
        filepath = self.savefilepath(
            self.table_name, caption, file_filter=self.EXCEL_FILTER
        )
        if filepath:
            if not filepath.endswith(".xlsx"):
                filepath += ".xlsx"
            self.model.to_excel(filepath)

    @Slot(QtGui.QKeyEvent, name="copyEvent")
    def keyPressEvent(self, e):
        """Allow user to copy selected data from the table

        NOTE: by default, the table headers (column names) are also copied.
        """
        if e.modifiers() & Qt.ControlModifier:
            # Should we include headers?
            headers = e.modifiers() & Qt.ShiftModifier
            if e.key() == Qt.Key_C:  # copy
                selection = [
                    self.model.proxy_to_source(p) for p in self.selectedIndexes()
                ]
                rows = [index.row() for index in selection]
                columns = [index.column() for index in selection]
                rows = sorted(set(rows), key=rows.index)
                columns = sorted(set(columns), key=columns.index)
                self.model.to_clipboard(rows, columns, headers)


class ABFilterableDataFrameView(ABDataFrameView):
    """Filterable base class for showing pandas dataframe objects as tables.

    To use this table, the following MUST be set in the table model:
    - self.filterable_columns: dict
        --> these columns are available for filtering
        --> key is column name, value is column index

    To use this table, the following MUST be set in the table view:
    - self.header.column_indices = list(self.model.filterable_columns.values())
        --> If not set, no filter buttons will appear.
        --> Probably wise to set in a `if isinstance(self.model.filterable_columns, dict):`
        --> This variable must be set any time the columns of the table change

    To use this table, the following can be set in the table model:
    - self.different_column_types: dict
        --> these columns require a different filter type than 'str'
        --> e.g. self.different_column_types = {'col_name': 'num'}
    """

    FILTER_TYPES = {
        "str": [
            "contains",
            "does not contain",
            "equals",
            "does not equal",
            "starts with",
            "does not start with",
            "ends with",
            "does not end with",
        ],
        "str_tt": [
            "values in the column contain",
            "values in the column do not contain",
            "values in the column equal",
            "values in the column do not equal",
            "values in the column start with",
            "values in the column do not start with",
            "values in the column end with",
            "values in the column do not end with",
        ],
        "num": ["=", "!=", ">=", "<=", "<= x <="],
        "num_tt": [
            "values in the column equal",
            "values in the column do not equal",
            "values in the column are greater than or equal to",
            "values in the column are smaller than or equal to",
            "values in the column are between",
        ],
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.header = CustomHeader()
        self.setHorizontalHeader(self.header)

        self.filters = None
        self.different_column_types = {}
        self.header.clicked.connect(self.header_filter_button_clicked)
        self.selected_column = 0

        # quick-filter setup:
        self.prev_quick_filter = {}
        self.debounce_quick_filter = QTimer()
        self.debounce_quick_filter.setInterval(300)
        self.debounce_quick_filter.setSingleShot(True)
        self.debounce_quick_filter.timeout.connect(self.quick_filter)

    def header_filter_button_clicked(self, column: int, button: str) -> None:
        self.selected_column = column
        # this function is separate from the context menu in case we want to add right-click options later
        if button == "LeftButton":
            self.header_context_menu()

    def header_context_menu(self) -> None:
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)

        col_type = self.model.different_column_types.get(
            {v: k for k, v in self.model.filterable_columns.items()}[
                self.selected_column
            ],
            "str",
        )

        # quick-filter bar
        self.input_line = QtWidgets.QLineEdit()
        self.input_line.setFocusPolicy(Qt.StrongFocus)
        if col_type == "num":
            self.input_line.setValidator(QtGui.QDoubleValidator())
        search = QtWidgets.QToolButton()
        search.setIcon(qicons.search)
        search.clicked.connect(menu.close)
        quick_filter_layout = QtWidgets.QHBoxLayout()
        quick_filter_layout.addWidget(self.input_line)
        quick_filter_layout.addWidget(search)
        quick_filter_widget = QtWidgets.QWidget()
        quick_filter_widget.setLayout(quick_filter_layout)
        quick_filter_widget.setToolTip(
            "Filter this column on the input,\n"
            "press 'enter' or the search button to filter"
        )
        # write previous filter to the quick-filter input if we have one
        if prev_filter := self.prev_quick_filter.get(self.selected_column, False):
            self.input_line.setText(prev_filter[1])
        else:
            self.input_line.setPlaceholderText("Quick filter ...")
        self.input_line.textChanged.connect(self.debounce_quick_filter.start)
        self.input_line.returnPressed.connect(menu.close)
        QAline = QtWidgets.QWidgetAction(self)
        QAline.setDefaultWidget(quick_filter_widget)
        menu.addAction(QAline)

        # More filters submenu
        mf_menu = QtWidgets.QMenu(menu)
        mf_menu.setToolTipsVisible(True)
        mf_menu.setIcon(qicons.filter)
        mf_menu.setTitle("More filters")
        filter_actions = []
        for i, f in enumerate(self.FILTER_TYPES[col_type]):
            fa = QtWidgets.QAction(text=f)
            fa.setToolTip(self.FILTER_TYPES[col_type + "_tt"][i])
            fa.triggered.connect(self.simple_filter_dialog)
            filter_actions.append(fa)
        for fa in filter_actions:
            mf_menu.addAction(fa)
        menu.addMenu(mf_menu)
        # edit filters main menu
        filter_man = QtWidgets.QAction(qicons.edit, "Manage filters")
        filter_man.triggered.connect(self.filter_manager_dialog)
        filter_man.setToolTip("Open the filter management menu")
        menu.addAction(filter_man)
        # delete column filters option
        col_del = QtWidgets.QAction(qicons.delete, "Remove column filters")
        col_del.triggered.connect(self.reset_column_filters)
        col_del.setToolTip("Remove all filters on this column")
        menu.addAction(col_del)
        col_del.setEnabled(False)
        if isinstance(self.filters, dict) and self.filters.get(
            self.selected_column, False
        ):
            col_del.setEnabled(True)
        # delete all filters option
        all_del = QtWidgets.QAction(qicons.delete, "Remove all filters")
        all_del.triggered.connect(self.reset_filters)
        all_del.setToolTip("Remove all filters in this table")
        menu.addAction(all_del)
        all_del.setEnabled(False)
        if isinstance(self.filters, dict):
            all_del.setEnabled(True)

        # Show existing filters for column
        if isinstance(self.filters, dict) and self.filters.get(
            self.selected_column, False
        ):
            menu.addSeparator()
            active_filters_label = QtWidgets.QAction(
                qicons.filter, "Active column filters:"
            )
            active_filters_label.setEnabled(False)
            menu.addAction(active_filters_label)
            active_filters = []
            for filter_data in self.filters[self.selected_column]["filters"]:
                if filter_data[0] == "<= x <=":
                    q = " and ".join(filter_data[1])
                else:
                    q = filter_data[1]
                filter_str = ": ".join([filter_data[0], q])
                f = QtWidgets.QAction(text=filter_str)
                f.setEnabled(False)
                active_filters.append(f)
            for f in active_filters:
                menu.addAction(f)

        self.input_line.setFocus()
        loc = self.header.event_pos
        menu.exec_(self.mapToGlobal(loc))

    @Slot(name="updateProxyModel")
    def update_proxy_model(self) -> None:
        self.proxy_model = ABMultiColumnSortProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

    def quick_filter(self) -> None:
        # remove weird whitespace from input
        query = (
            self.input_line.text().translate(str.maketrans("", "", "\n\t\r")).strip()
        )

        # convert to filter
        col_name = {v: k for k, v in self.model.filterable_columns.items()}[
            self.selected_column
        ]
        if self.model.different_column_types.get(col_name):
            # column is type 'num'
            filt = ("=", query)
        else:
            # column is type 'str'
            filt = ("contains", query, False)
        # check if quick filter exists for this col, if so; remove from self.filters
        if prev_filter := self.prev_quick_filter.get(self.selected_column, False):
            self.filters[self.selected_column]["filters"].remove(prev_filter)

        # place the filter in self.prev_quick_filter for next quick filter on this column
        self.prev_quick_filter[self.selected_column] = filt

        # apply the right filters
        if query != "":
            # the query is not empty, add it to the filters and apply them
            self.add_filter(filt)
            self.apply_filters()
        elif len(self.filters[self.selected_column]["filters"]) > 0:
            # the query is empty, but there are still filters for this column, so apply the filters
            self.apply_filters()
        else:
            # the query is empty, and there are no more filters for this column, reset this filter.
            self.reset_column_filters()

    def filter_manager_dialog(self) -> None:
        # get right data
        column_names = self.model.filterable_columns

        # show dialog
        dialog = FilterManagerDialog(
            column_names=column_names,
            filters=self.filters,
            filter_types=self.FILTER_TYPES,
            selected_column=self.selected_column,
            column_types=self.model.different_column_types,
        )
        if dialog.exec_() == FilterManagerDialog.Accepted:
            # set the filters
            filters = dialog.get_filters
            if filters != self.filters:
                # the filters returned from the dialog are different, actually apply the filters
                rm = []
                for col, qf in self.prev_quick_filter.items():
                    # check if quickfilters exist for these columns, otherwise remove them
                    if (
                        filters.get(col, False) and qf not in filters[col]["filters"]
                    ) or not filters.get(col, False):
                        rm.append(col)
                for col in rm:
                    self.prev_quick_filter.pop(col)
                self.write_filters(filters)
                self.apply_filters()

    def simple_filter_dialog(self, preset_type: str = None) -> None:
        if not preset_type:
            preset_type = self.sender().text()

        # get right data
        column_name = {v: k for k, v in self.model.filterable_columns.items()}[
            self.selected_column
        ]
        col_type = self.model.different_column_types.get(column_name, "str")

        # show dialog
        dialog = SimpleFilterDialog(
            column_name=column_name,
            filter_types=self.FILTER_TYPES,
            column_type=col_type,
            preset_type=preset_type,
        )
        if dialog.exec_() == SimpleFilterDialog.Accepted:
            new_filter = dialog.get_filter
            # add the filter to existing filters
            if new_filter:
                self.add_filter(new_filter)
                self.apply_filters()

    def add_filter(self, new_filter: tuple) -> None:
        """Add a single filter to self.filters."""
        if isinstance(self.filters, dict):
            # filters exist
            all_filters = self.filters
            if all_filters.get(self.selected_column, False):
                # filters exist for this column
                all_filters[self.selected_column]["filters"].append(new_filter)
                if (
                    not all_filters[self.selected_column].get("mode", False)
                    and len(all_filters[self.selected_column]["filters"]) > 1
                ):
                    # a mode does not exist, but there are multiple filters
                    all_filters[self.selected_column]["mode"] = "OR"
            else:
                # filters don't yet exist for this column:
                all_filters[self.selected_column] = {"filters": [new_filter]}
        else:
            # no filters exist
            all_filters = {
                self.selected_column: {"filters": [new_filter]},
                "mode": "AND",
            }

        self.write_filters(all_filters)

    def write_filters(self, filters: dict) -> None:
        self.filters = filters

    def apply_filters(self) -> None:
        if self.filters:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            # only allow filters that are for columns that may be filtered on
            filters = {
                k: v
                for k, v in self.filters.items()
                if k in list(self.model.filterable_columns.values()) + ["mode"]
            }
            self.proxy_model.set_filters(self.model.get_filter_mask(filters))
            self.header.has_active_filters = list(filters.keys())
            QtWidgets.QApplication.restoreOverrideCursor()
        else:
            self.reset_filters()

    def reset_column_filters(self) -> None:
        """Reset all filters for this column."""
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        f = self.filters
        if f.get(self.selected_column, False):
            f.pop(self.selected_column)
        if self.prev_quick_filter.get(self.selected_column, False):
            self.prev_quick_filter.pop(self.selected_column)
        self.write_filters(f)
        if len(self.filters) == 1 and self.filters.get("mode"):
            # the only thing in filters remaining is the mode --> there are no filters
            self.reset_filters()
        else:
            self.header.has_active_filters = list(self.filters.keys())
            self.apply_filters()
        QtWidgets.QApplication.restoreOverrideCursor()

    def reset_filters(self) -> None:
        """Reset all filters for this entire table."""
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        self.write_filters(None)
        self.header.has_active_filters = []
        self.prev_quick_filter = {}
        self.proxy_model.clear_filters()
        QtWidgets.QApplication.restoreOverrideCursor()


class LCAResultsModel(PandasModel):
    def sync(self, df):
        self._dataframe = df.replace(np.nan, "", regex=True)
        self.updated.emit()


class LCAResultsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LCAResultsModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)


class InventoryModel(PandasModel):
    def sync(self, df):
        self._dataframe = df
        # set the visible columns
        self.filterable_columns = {
            col: i for i, col in enumerate(self._dataframe.columns.to_list())
        }
        # set the columns te be defined as num (all except the first five for both biopshere and technosphere
        self.different_column_types = {
            col: "num"
            for i, col in enumerate(self._dataframe.columns.to_list())
            if i >= 5
        }
        self.updated.emit()


class InventoryTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setStretchLastSection(True)

        self.model = InventoryModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.update_filter_data)
        # below variables are required for switching between technosphere and biosphere tables
        self.showing = None
        self.filters_tec = None
        self.filters_bio = None

    def update_filter_data(self) -> None:
        if self.showing == "technosphere":
            self.filters = self.filters_tec
        else:
            self.filters = self.filters_bio

        # update the column header indices
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())
        # apply the existing filters
        self.apply_filters()

    def write_filters(self, filters: dict) -> None:
        if self.showing == "technosphere":
            self.filters_tec = filters
        else:
            self.filters_bio = filters
        self.filters = filters


class ContributionModel(PandasModel):
    def sync(self, df, unit="relative share"):

        if "unit" in df.columns:
            # overwrite the unit col with 'relative share' if looking at relative results (except 3 'total' and 'rest' rows)
            df["unit"] = [""] * 3 + [unit] * (len(df) - 3)

        # drop any rows where all numbers are 0
        self._dataframe = df.loc[~(df.select_dtypes(include=np.number) == 0).all(axis=1)]
        self.updated.emit()


class ContributionTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ContributionModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
