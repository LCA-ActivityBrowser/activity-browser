# -*- coding: utf-8 -*-
import os
from typing import Optional

from bw2data.filesystem import safe_filename
from PySide2.QtCore import QSize, QSortFilterProxyModel, Qt, Slot, QPoint, Signal, QRect, QTimer
from PySide2.QtWidgets import QFileDialog, QTableView, QTreeView, QApplication, QMenu, QAction, \
    QHeaderView, QStyle, QStyleOptionButton,QLineEdit, QWidgetAction, QWidget, QHBoxLayout, QToolButton
from PySide2.QtGui import QKeyEvent, QDoubleValidator

from ...settings import ab_settings
from ..widgets.dialog import FilterManagerDialog, SimpleFilterDialog
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
        'str': ['contains', 'does not contain',
                'equals', 'does not equal',
                'starts with', 'does not start with',
                'ends with', 'does not end with'],
        'str_tt': ['values in the column contain', 'values in the column do not contain',
                   'values in the column equal', 'values in the column do not equal',
                   'values in the column start with', 'values in the column do not start with',
                   'values in the column end with', 'values in the column do not end with'],
        'num': ['=', '!=', '>=', '<=', '<= x <='],
        'num_tt': ['values in the column equal', 'values in the column do not equal',
                   'values in the column are greater than or equal to',
                   'values in the column are smaller than or equal to',
                   'values in the column are between']
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
        if button == 'LeftButton':
            self.header_context_menu()

    def header_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setToolTipsVisible(True)

        col_type = self.model.different_column_types.get(
            {v: k for k, v in self.model.filterable_columns.items()}[self.selected_column],
            'str')

        # quick-filter bar
        self.input_line = QLineEdit()
        self.input_line.setFocusPolicy(Qt.StrongFocus)
        if col_type == 'num':
            self.input_line.setValidator(QDoubleValidator())
        search = QToolButton()
        search.setIcon(qicons.search)
        search.clicked.connect(menu.close)
        quick_filter_layout = QHBoxLayout()
        quick_filter_layout.addWidget(self.input_line)
        quick_filter_layout.addWidget(search)
        quick_filter_widget = QWidget()
        quick_filter_widget.setLayout(quick_filter_layout)
        quick_filter_widget.setToolTip("Filter this column on the input,\n"
                                       "press 'enter' or the search button to filter")
        # write previous filter to the quick-filter input if we have one
        if prev_filter := self.prev_quick_filter.get(self.selected_column, False):
            self.input_line.setText(prev_filter[1])
        else:
            self.input_line.setPlaceholderText('Quick filter ...')
        self.input_line.textChanged.connect(self.debounce_quick_filter.start)
        self.input_line.returnPressed.connect(menu.close)
        QAline = QWidgetAction(self)
        QAline.setDefaultWidget(quick_filter_widget)
        menu.addAction(QAline)

        # More filters submenu
        mf_menu = QMenu(menu)
        mf_menu.setToolTipsVisible(True)
        mf_menu.setIcon(qicons.filter)
        mf_menu.setTitle('More filters')
        filter_actions = []
        for i, f in enumerate(self.FILTER_TYPES[col_type]):
            fa = QAction(text=f)
            fa.setToolTip(self.FILTER_TYPES[col_type + '_tt'][i])
            fa.triggered.connect(self.simple_filter_dialog)
            filter_actions.append(fa)
        for fa in filter_actions:
            mf_menu.addAction(fa)
        menu.addMenu(mf_menu)
        # edit filters main menu
        filter_man = QAction(qicons.edit, 'Manage filters')
        filter_man.triggered.connect(self.filter_manager_dialog)
        filter_man.setToolTip("Open the filter management menu")
        menu.addAction(filter_man)
        # delete column filters option
        col_del = QAction(qicons.delete, 'Remove column filters')
        col_del.triggered.connect(self.reset_column_filters)
        col_del.setToolTip('Remove all filters on this column')
        menu.addAction(col_del)
        col_del.setEnabled(False)
        if isinstance(self.filters, dict) and self.filters.get(self.selected_column, False):
            col_del.setEnabled(True)
        # delete all filters option
        all_del = QAction(qicons.delete, 'Remove all filters')
        all_del.triggered.connect(self.reset_filters)
        all_del.setToolTip('Remove all filters in this table')
        menu.addAction(all_del)
        all_del.setEnabled(False)
        if isinstance(self.filters, dict):
            all_del.setEnabled(True)

        # Show existing filters for column
        if isinstance(self.filters, dict) and self.filters.get(self.selected_column, False):
            menu.addSeparator()
            active_filters_label = QAction(qicons.filter, 'Active column filters:')
            active_filters_label.setEnabled(False)
            menu.addAction(active_filters_label)
            active_filters = []
            for filter_data in self.filters[self.selected_column]['filters']:
                if filter_data[0] == '<= x <=':
                    q = ' and '.join(filter_data[1])
                else:
                    q = filter_data[1]
                filter_str = ': '.join([filter_data[0], q])
                f = QAction(text=filter_str)
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
        query = self.input_line.text().translate(str.maketrans('', '', '\n\t\r'))

        # convert to filter
        col_name = {v: k for k, v in self.model.filterable_columns.items()}[self.selected_column]
        if self.model.different_column_types.get(col_name):
            # column is type 'num'
            filt = ('=', query)
        else:
            # column is type 'str'
            filt = ('contains', query, False)
        # check if quick filter exists for this col, if so; remove from self.filters
        if prev_filter := self.prev_quick_filter.get(self.selected_column, False):
            self.filters[self.selected_column]['filters'].remove(prev_filter)

        # place the filter in self.prev_quick_filter for next quick filter on this column
        self.prev_quick_filter[self.selected_column] = filt

        # apply the right filters
        if query != '':
            # the query is not empty, add it to the filters and apply them
            self.add_filter(filt)
            self.apply_filters()
        elif len(self.filters[self.selected_column]['filters']) > 0:
            # the query is empty, but there are still filters for this column, so apply the filters
            self.apply_filters()
        else:
            # the query is empty, and there are no more filters for this column, reset this filter.
            self.reset_column_filters()

    def filter_manager_dialog(self) -> None:
        # get right data
        column_names = self.model.filterable_columns

        # show dialog
        dialog = FilterManagerDialog(column_names=column_names,
                                     filters=self.filters,
                                     filter_types=self.FILTER_TYPES,
                                     selected_column=self.selected_column,
                                     column_types=self.model.different_column_types)
        if dialog.exec_() == FilterManagerDialog.Accepted:
            # set the filters
            filters = dialog.get_filters
            if filters != self.filters:
                # the filters returned from the dialog are different, actually apply the filters
                rm = []
                for col, qf in self.prev_quick_filter.items():
                    # check if quickfilters exist for these columns, otherwise remove them
                    if (filters.get(col, False) and qf not in filters[col]['filters']) or not filters.get(col, False):
                        rm.append(col)
                for col in rm:
                    self.prev_quick_filter.pop(col)
                self.write_filters(filters)
                self.apply_filters()

    def simple_filter_dialog(self, preset_type: str = None) -> None:
        if not preset_type:
            preset_type = self.sender().text()

        # get right data
        column_name = {v: k for k, v in self.model.filterable_columns.items()}[self.selected_column]
        col_type = self.model.different_column_types.get(column_name, 'str')

        # show dialog
        dialog = SimpleFilterDialog(column_name=column_name,
                                    filter_types=self.FILTER_TYPES,
                                    column_type=col_type,
                                    preset_type=preset_type)
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
                all_filters[self.selected_column]['filters'].append(new_filter)
                if not all_filters[self.selected_column].get('mode', False) \
                        and len(all_filters[self.selected_column]['filters']) > 1:
                    # a mode does not exist, but there are multiple filters
                    all_filters[self.selected_column]['mode'] = 'OR'
            else:
                # filters don't yet exist for this column:
                all_filters[self.selected_column] = {'filters': [new_filter]}
        else:
            # no filters exist
            all_filters = {self.selected_column: {'filters': [new_filter]},
                           'mode': 'AND'}

        self.write_filters(all_filters)

    def write_filters(self, filters: dict) -> None:
        self.filters = filters

    def apply_filters(self) -> None:
        if self.filters:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            # only allow filters that are for columns that may be filtered on
            filters = {k: v for k, v in self.filters.items() if k in list(self.model.filterable_columns.values()) + ['mode']}
            self.proxy_model.set_filters(self.model.get_filter_mask(filters))
            self.header.has_active_filters = list(filters.keys())
            QApplication.restoreOverrideCursor()
        else:
            self.reset_filters()

    def reset_column_filters(self) -> None:
        """Reset all filters for this column."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        f = self.filters
        f.pop(self.selected_column)
        if self.prev_quick_filter.get(self.selected_column, False):
            self.prev_quick_filter.pop(self.selected_column)
        self.write_filters(f)
        if len(self.filters) == 1 and self.filters.get('mode'):
            # the only thing in filters remaining is the mode --> there are no filters
            self.reset_filters()
        else:
            self.header.has_active_filters = list(self.filters.keys())
            self.apply_filters()
        QApplication.restoreOverrideCursor()

    def reset_filters(self) -> None:
        """Reset all filters for this entire table."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.write_filters(None)
        self.header.has_active_filters = []
        self.prev_quick_filter = {}
        self.proxy_model.clear_filters()
        QApplication.restoreOverrideCursor()


class CustomHeader(QHeaderView):
    """Header which has a filter button on each cell that can trigger a signal.

    Largely based on https://stackoverflow.com/a/30938728
    """
    clicked = Signal(int, str)

    _x_offset = 0
    _y_offset = 0  # This value is calculated later, based on the height of the paint rect
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
            option = QStyleOptionButton()
            option.rect = QRect(rect.x() + self._x_offset, rect.y() + self._y_offset, self._width, self._height)
            option.state = QStyle.State_Enabled | QStyle.State_Active

            # put the filter icon onto the label
            if logical_index in self.has_active_filters:
                option.icon = qicons.filter
            else:
                option.icon = qicons.filter_outline
            option.iconSize = QSize(16, 16)

            # set the settings to a PushButton
            self.style().drawControl(QStyle.CE_PushButton, option, painter)

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index in self.column_indices:
            x = self.sectionPosition(index)
            if x + self._x_offset < event.pos().x() < x + self._x_offset + self._width \
                    and self._y_offset < event.pos().y() < self._y_offset + self._height:
                # the button is clicked

                # set the position of the lower left point of the filter button to spawn a menu
                pos = QPoint()
                pos.setX(x + self._x_offset + self._width)
                pos.setY(self._y_offset + self._height)
                self.event_pos = pos

                # emit the column index and the button (left/right) pressed
                self.clicked.emit(index, str(event.button()).split('.')[-1])
            else:
                # pass the event to the header (for sorting)
                super(CustomHeader, self).mousePressEvent(event)
        else:
            # pass the event to the header (for sorting)
            super(CustomHeader, self).mousePressEvent(event)
        self.viewport().update()


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
        print('{} filter matches found'.format(self.matches))

    def clear_filters(self) -> None:
        self.mask = None
        self.invalidateFilter()

    def filterAcceptsRow(self, row: int, parent) -> bool:
        # check if self.activate_filter is enabled, else return True
        if not self.activate_filter:
            return True
        # get the right index from the mask
        matched = self.mask.iloc[row]
        if matched: self.matches += 1
        return matched


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
