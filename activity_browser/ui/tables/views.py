# -*- coding: utf-8 -*-
import os
from functools import wraps
from typing import Optional

from bw2data.filesystem import safe_filename
from PySide2.QtCore import QSize, QSortFilterProxyModel, Qt, Slot
from PySide2.QtWidgets import QFileDialog, QTableView, QTreeView
from PySide2.QtGui import QKeyEvent

from ...settings import ab_settings
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
