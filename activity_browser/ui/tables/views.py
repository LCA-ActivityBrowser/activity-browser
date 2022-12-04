# -*- coding: utf-8 -*-
import os
from functools import wraps
from typing import Optional

from bw2data.filesystem import safe_filename
from PySide2.QtCore import QSize, QSortFilterProxyModel, Qt, Slot, QPoint
from PySide2.QtWidgets import QFileDialog, QTableView, QTreeView, QApplication, QMenu, QAction
from PySide2.QtGui import QKeyEvent

from ...settings import ab_settings
from ..widgets.dialog import TableFilterDialog
from ..icons import qicons
from .delegates import ViewOnlyDelegate
from .models import PandasModel


class ABDataFrameView(QTableView):
    """ Base class for showing pandas dataframe objects as tables.
    """
    ALL_FILTER = "All Files (*.*)"
    CSV_FILTER = "CSV (*.csv);; All Files (*.*)"
    TSV_FILTER = "TSV (*.tsv);; All Files (*.*)"
    EXCEL_FILTER = "Excel (*.xlsx);; All Files (*.*)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.verticalHeader().setDefaultSectionSize(22)  # row height
        self.verticalHeader().setVisible(True)
        # Use a custom ViewOnly delegate by default.
        # Can be overridden table-wide or per column in child classes.
        self.setItemDelegate(ViewOnlyDelegate(self))

        self.table_name = 'LCA results'
        # Initialize attributes which are set during the `sync` step.
        # Creating (and typing) them here allows PyCharm to see them as
        # valid attributes.
        self.model: Optional[PandasModel] = None
        self.proxy_model: Optional[QSortFilterProxyModel] = None

    def get_max_height(self) -> int:
        return (self.verticalHeader().count())*self.verticalHeader().defaultSectionSize() + \
                 self.horizontalHeader().height() + self.horizontalScrollBar().height() + 5

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.get_max_height())

    def rowCount(self) -> int:
        return 0 if self.model is None else self.model.rowCount()

    @Slot(name="updateProxyModel")
    def update_proxy_model(self) -> None:
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Custom table resizing to perform after setting new (proxy) model.
        """
        self.setMaximumHeight(self.get_max_height())

    @Slot(name="exportToClipboard")
    def to_clipboard(self):
        """ Copy dataframe to clipboard
        """
        rows = list(range(self.model.rowCount()))
        cols = list(range(self.model.columnCount()))
        self.model.to_clipboard(rows, cols, include_header=True)

    def savefilepath(self, default_file_name: str, caption: str = None, file_filter: str = None):
        """ Construct and return default path where data is stored

        Uses the application directory for AB
        """
        safe_name = safe_filename(default_file_name, add_hash=False)
        caption = caption or "Choose location to save lca results"
        filepath, _ = QFileDialog.getSaveFileName(
            parent=self, caption=caption,
            dir=os.path.join(ab_settings.data_dir, safe_name),
            filter=file_filter or self.ALL_FILTER,
        )
        # getSaveFileName can now weirdly return Path objects.
        return str(filepath) if filepath else filepath

    @Slot(name="exportToCsv")
    def to_csv(self):
        """ Save the dataframe data to a CSV file.
        """
        filepath = self.savefilepath(self.table_name, file_filter=self.CSV_FILTER)
        if filepath:
            if not filepath.endswith('.csv'):
                filepath += '.csv'
            self.model.to_csv(filepath)

    @Slot(name="exportToExcel")
    def to_excel(self, caption: str = None):
        """ Save the dataframe data to an excel file.
        """
        filepath = self.savefilepath(self.table_name, caption, file_filter=self.EXCEL_FILTER)
        if filepath:
            if not filepath.endswith('.xlsx'):
                filepath += '.xlsx'
            self.model.to_excel(filepath)

    @Slot(QKeyEvent, name="copyEvent")
    def keyPressEvent(self, e):
        """ Allow user to copy selected data from the table

        NOTE: by default, the table headers (column names) are also copied.
        """
        if e.modifiers() & Qt.ControlModifier:
            # Should we include headers?
            headers = e.modifiers() & Qt.ShiftModifier
            if e.key() == Qt.Key_C:  # copy
                selection = [self.model.proxy_to_source(p) for p in self.selectedIndexes()]
                rows = [index.row() for index in selection]
                columns = [index.column() for index in selection]
                rows = sorted(set(rows), key=rows.index)
                columns = sorted(set(columns), key=columns.index)
                self.model.to_clipboard(rows, columns, headers)


class ABFilterableDataFrameView(ABDataFrameView):
    """ Filterable base class for showing pandas dataframe objects as tables.
            """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.headerContextMenuEvent)

        self.filters = None

    def headerContextMenuEvent(self, local_pos: QPoint) -> None:
        index = self.indexAt(local_pos)
        column = int(index.column())
        if index.row() == -1:
            return

        menu = QMenu(self)
        # Show options for managing filters
        menu.addAction(
            qicons.add, 'Add Filter',
            lambda: self.start_filter_dialog(column))
        menu.addAction(
            qicons.delete, 'Remove all filters in this column',
            lambda: self.reset_column_filters(column))
        menu.addAction(
            qicons.delete, 'Remove all filters in this table',
            lambda: self.reset_filters())

        # Show existing filters for column
        if isinstance(self.filters, dict) and self.filters.get(column, False):
            sub_menu = QMenu(menu)
            sub_menu.setTitle('Active filters on column')
            filter_entries = []
            for filter in self.filters[index.column()]['filters']:
                filter_str = ': '.join([filter[0], filter[1]])
                f_menu = QAction(qicons.filter_icon, filter_str)
                f_menu.setEnabled(False)
                filter_entries.append(f_menu)
            for f_menu in filter_entries:
                sub_menu.addAction(f_menu)
            menu.addMenu(sub_menu)

        menu.exec_(self.mapToGlobal(local_pos))

    @Slot(name="updateProxyModel")
    def update_proxy_model(self) -> None:
        self.proxy_model = ABMultiColumnSortProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

    def start_filter_dialog(self, selected_column: int = 0) -> None:
        # get right data
        column_names = self.model.visible_columns

        # show dialog
        dialog = TableFilterDialog(column_names, self.filters, selected_column=selected_column)
        if dialog.exec_() == TableFilterDialog.Accepted:
            filters = dialog.get_filters
            self.filters = filters
            self.apply_filters()

    def apply_filters(self) -> None:
        # if a column sort order is possible, use [key, activity, product, classification, location, unit]
        # each option is less likely to cut out many options than the last one
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.proxy_model.set_filters(self.filters)
        QApplication.restoreOverrideCursor()

    def reset_column_filters(self, idx: int) -> None:
        """Reset all filters for this column"""
        self.filters.pop(idx)
        self.apply_filters()

    def reset_filters(self) -> None:
        self.filters = None


class ABMultiColumnSortProxyModel(QSortFilterProxyModel):
    """ Subclass of QSortFilterProxyModel to enable sorting on multiple columns.

    The main purpose of this subclass is to override def filterAcceptsRow().

    Subclass based on various ideas from:
    https://stackoverflow.com/questions/47201539/how-to-filter-multiple-column-in-qtableview
    http://www.dayofthenewdan.com/2013/02/09/Qt_QSortFilterProxyModel.html
    https://gist.github.com/dbridges/4732790
    """
    def __init__(self, parent=None):
        super(ABMultiColumnSortProxyModel, self).__init__(parent)

        # filter_mode should be AND or OR
        # defines how filter on different columns is combined
        self.filter_mode = 'AND'

        # filters contains all filters used as a list per column
        # example:
        # self.filters = {
        #     0: {'filters': [('contains', 'heat', False), ('contains', 'electricity', False)],
        #         'mode': 'OR'},
        #     1: {'filters': [('contains', 'market', False)]}
        # }
        # this would filter for heat OR electricity in column 0 (Products) and in column 1 (Activity) for market.
        # filters is a required argument for each column that is filtered and is a list of tuples.
        # list elements contain a tuple with the search mode, the search term and if searching on string,
        # a boolean for case sensitive.
        # mode is optional and regards how the filters are combined within a column and is either "AND" or "OR"
        #
        self.filters = {}

        # custom_column_order can be used to optimize the order of columns being searched IF the filter_mode is AND
        # custom_column_order should be written as list with column indices,
        # ordered from most important to least important
        self.custom_column_order = None

    def set_filters(self, filters: dict) -> None:
        if filters.get('mode', False):
            self.filter_mode = filters['mode']
            filters.pop('mode')
            self.filters = filters
            self.invalidateFilter()
            self.filters['mode'] = self.filter_mode
        else:
            print("WARNING: missing filter mode, assuming 'AND'")
            self.clear_filters()

    def clear_filters(self) -> None:
        self.filters = {}
        self.invalidateFilter()

    def tester(self, test_type: str, a, b) -> bool:
        """Compare a and b on test_type.
        a = filter term
        b = column value
        """
        if test_type == 'equals' or test_type == '=':
            return a == b
        elif test_type == 'does not equal' or test_type == '!=':
            return a != b
        elif test_type == 'contains':
            return a in b
        elif test_type == 'does not contain':
            return a not in b
        elif test_type == 'starts with':
            return b.startswith(a)
        elif test_type == 'does not start with':
            return not b.startswith(a)
        elif test_type == 'ends with':
            return b.endswith(a)
        elif test_type == 'does not end with':
            return not b.endswith(a)
        elif test_type == '>=':
            return b >= a
        elif test_type == '<=':
            return b >= a
        else:
            print("WARNING: unknown filter type >{}<, assuming 'EQUALS'".format(test_type))
            return a == b

    def apply_filter_tests(self, idx: int, value) -> bool:
        """Apply all filter tests in self.filters for column idx.

        Return a boolean whether or not the tests for column idx pass
        """
        filter_tests = self.filters.get(idx)

        # iterate over each test and call self.tester with the right data for each test
        tests = []
        for test in filter_tests['filters']:
            test_type, filter_val = test[0], test[1]
            if len(test) == 3 and not test[2]:
                # test[2] is a bool for case sensitivity
                filter_val, value = str(filter_val).lower(), str(value).lower()
                test_result = self.tester(test_type, str(filter_val), str(value))
            else:
                test_result = self.tester(test_type, filter_val, value)
            tests.append(test_result)

        if len(tests) > 1:
            if filter_tests['mode'] == "OR":
                return any(tests)
            else:
                return all(tests)
        return all(tests)

    def filterAcceptsRow(self, row: int, parent) -> bool:
        """Iterate over each column in the row and test the filters in self.filters for relevant columns.

        Return a boolean whether or not to keep the row.
        """
        # get the data of the row
        row_data = self.sourceModel().row_data(row)

        # if a custom order is defined, use it, else just go from left to right
        if isinstance(self.custom_column_order, dict):
            column_order = self.custom_column_order
        else:
            column_order = [i for i in range(len(row_data))]

        # iterate over each column in the row and apply filter tests
        tests = []
        for i in column_order:
            if i in self.filters.keys():
                col_data = row_data[i]
                test = self.apply_filter_tests(idx=i, value=col_data)
                if test == False and self.filter_mode == "AND":
                    return False
                tests.append(test)

        if self.filter_mode == 'AND':
            return all(tests)
        elif self.filter_mode == 'OR':
            return any(tests)
        else:
            print("WARNING: unknown filter mode >{}<, assuming 'AND'".format(self.filter_mode))
            return all(tests)


class ABDictTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUniformRowHeights(True)
        self.data = {}
        self._connect_signals()

    def _connect_signals(self):
        self.expanded.connect(self.custom_view_sizing)
        self.collapsed.connect(self.custom_view_sizing)

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Resize the first column (usually 'name') whenever an item is
        expanded or collapsed.
        """
        self.resizeColumnToContents(0)

    @Slot(name="expandSelectedBranch")
    def expand_branch(self):
        """Expand selected branch."""
        index = self.currentIndex()
        self.expand_or_collapse(index, True)

    @Slot(name="collapseSelectedBranch")
    def collapse_branch(self):
        """Collapse selected branch."""
        index = self.currentIndex()
        self.expand_or_collapse(index, False)

    def expand_or_collapse(self, index, expand):
        """Expand or collapse branch.

        Will expand or collapse any branch and sub-branches given in index.
        expand is a boolean that defines expand (True) or collapse (False)."""
        # based on: https://stackoverflow.com/a/4208240

        def recursive_expand_or_collapse(index, childCount, expand):

            for childNo in range(0, childCount):
                childIndex = index.child(childNo, 0)
                if expand:  # if expanding, do that first (wonky animation otherwise)
                    self.setExpanded(childIndex, expand)
                subChildCount = childIndex.internalPointer().childCount()
                if subChildCount > 0:
                    recursive_expand_or_collapse(childIndex, subChildCount, expand)
                if not expand:  # if collapsing, do it last (wonky animation otherwise)
                    self.setExpanded(childIndex, expand)

        if not expand:  # if collapsing, do that first (wonky animation otherwise)
            self.setExpanded(index, expand)
        childCount = index.internalPointer().childCount()
        recursive_expand_or_collapse(index, childCount, expand)
        if expand:  # if expanding, do that last (wonky animation otherwise)
            self.setExpanded(index, expand)
