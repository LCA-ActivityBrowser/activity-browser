from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

from activity_browser.ui.icons import qicons

from .style import vertical_line


class ColumnFilterTab(QtWidgets.QWidget):
    """Content of column tab.

    Required inputs:
    - None
    Optional inputs:
    - col_type: str --> the type of column, either 'str' or 'num'. defines the search type options.
    defaults to 'str'
    - state: dict --> dict of existing filter state that should be re-created in UI.

    Interaction:
    - def get_state: Provides the state of all relevant filter elements (filter rows, AND/OR menu)
    returns: dict
    - def set_state: Writes given state dict to UI elements (filter rows, AND/OR menu)
    """

    def __init__(
        self, filter_types: dict, col_type: str = "str", state: dict = {}, parent=None
    ):
        super().__init__(parent)
        self.filter_types = filter_types
        self.col_type = col_type

        self.add = QtWidgets.QToolButton()
        self.add.setIcon(qicons.add)
        self.add.setToolTip("Add a new filter for this column")
        self.add.clicked.connect(self.add_row)

        self.and_or_buttons = AndOrRadioButtons(
            label_text="Combine filters within column:"
        )
        if self.col_type == "str":
            self.and_or_buttons.set_state("OR")

        self.filter_rows = []
        self.filter_widget_layout = QtWidgets.QVBoxLayout()
        self.filter_widget = QtWidgets.QWidget()
        self.filter_widget.setLayout(self.filter_widget_layout)

        # set the state, adds 1 empty row if state=={}
        self.set_state(state)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.filter_widget)
        layout.addWidget(self.add)
        layout.addStretch()
        layout.addWidget(self.and_or_buttons)
        self.setLayout(layout)

    def add_row(self, state: tuple = None) -> None:
        """Add a new row to the self.filter_rows."""
        idx = len(self.filter_rows)

        if self.col_type == "num":
            new_filter_row = NumFilterRow(
                idx=idx, state=state, filter_types=self.filter_types, parent=self
            )
        else:
            # if none of the above types, assume str
            new_filter_row = StrFilterRow(
                idx=idx, state=state, filter_types=self.filter_types, parent=self
            )

        self.filter_rows.append(new_filter_row)
        self.filter_widget_layout.addWidget(new_filter_row)
        self.show_hide_and_or()

    def remove_row(self, idx: int) -> None:
        """Remove the row from the setup"""
        # remove the row from widget and self.filter_rows
        self.filter_widget_layout.itemAt(idx).widget().deleteLater()
        self.filter_rows.pop(idx)
        # re-index the list of rows
        for i, filter_row in enumerate(self.filter_rows):
            filter_row.idx = i
        # if there would be no remaining rows, add a new empty one
        if len(self.filter_rows) == 0:
            self.add_row()
        self.show_hide_and_or()

    @property
    def get_state(self) -> dict:
        # check if there are filters
        if len(self.filter_rows) == 0:
            return None
        # check if there are valid filters
        valid_filters = [row.get_state for row in self.filter_rows if row.get_state]
        if len(valid_filters) == 0:
            return None
        elif len(valid_filters) == 1:
            return {"filters": valid_filters}
        else:
            return {"filters": valid_filters, "mode": self.and_or_buttons.get_state}

    def set_state(self, state: dict) -> None:
        if not state:
            self.add_row()
            self.and_or_buttons.hide()
            return

        # add one row per filter
        filters = state["filters"]
        self.filter_rows = []
        for filter_state in filters:
            self.add_row(filter_state)

        # set state and show/hide the AND/OR widget
        self.show_hide_and_or()
        if state.get("mode", False):
            self.and_or_buttons.set_state(state["mode"])

    def show_hide_and_or(self) -> None:
        if len(self.filter_rows) > 1:
            self.and_or_buttons.show()
        else:
            self.and_or_buttons.hide()


class AndOrRadioButtons(QtWidgets.QWidget):
    """Convenience class for managing AND/OR buttons.

    This class is purely intended for FilterManagerDialog and related, take this into account if using elsewhere.

    Required inputs:
    - None
    Optional inputs:
    - label_text: str -->
    - state: str --> str of existing AND/OR state that should be re-created in UI.

    Interaction:
    - def get_state: Provides the state of AND/OR radio buttons (string of 'AND' or 'OR')
    returns: str
    - def set_state: Writes given AND/OR state UI element (string of 'AND' or 'OR')
    """

    def __init__(self, label_text: str = "", state: str = None, parent=None):
        super().__init__(parent)
        # create an AND/OR widget
        layout = QtWidgets.QHBoxLayout()
        self.btn_group = QtWidgets.QButtonGroup()
        self.AND = QtWidgets.QRadioButton("AND")
        self.OR = QtWidgets.QRadioButton("OR")
        self.btn_group.addButton(self.AND)
        self.btn_group.addButton(self.OR)
        layout.addStretch()
        layout.addWidget(QtWidgets.QLabel(label_text))
        layout.addWidget(self.AND)
        layout.addWidget(self.OR)
        self.setLayout(layout)
        self.setToolTip(
            "Choose how filters combine with each other.\n"
            "AND must satisfy all filters, OR must satisfy at least one filter."
        )

        # set the state if one was given, otherwise, assume AND
        if isinstance(state, str):
            self.set_state(state)
        else:
            self.set_state("AND")

    @property
    def get_state(self) -> str:
        return self.btn_group.checkedButton().text()

    def set_state(self, state: str) -> None:
        x = True
        if state == "OR":
            x = False
        self.AND.setChecked(x)
        self.OR.setChecked(not x)


class FilterRow(QtWidgets.QWidget):
    """Convenience class for managing a filter input row.

    This class is purely intended for FilterManagerDialog and related, take this into account if using elsewhere.

    Required inputs:
    - idx: int --> integer index in self.filter_rows of parent. Used as ID in parent
    idx is the index position of this FilterRow in the list of rows in parent.
    - filter_types: dict --> the types of filter available
    Optional inputs:
    - state: tuple --> tuple of existing filter state that should be re-created in UI.

    Interaction:
    - def get_state: Provides the state of all relevant filter fields (filter type, query, case sensitive)
    returns: tuple
    - def set_state: Writes given state tuple to UI elements (filter type, query, case sensitive)
    """

    def __init__(
        self,
        idx: int,
        filter_types: dict,
        remove_option: bool = True,
        preset_type: str = None,
        parent=None,
    ):
        super().__init__(parent)

        self.idx = idx
        self.filter_types = filter_types
        self.filter_type = self.filter_types[self.column_type]
        self.parent = parent

        self.row_layout = QtWidgets.QHBoxLayout()

        # create a 'filter type' combobox
        self.filter_type_box = QtWidgets.QComboBox()
        self.filter_type_box.addItems(self.filter_type)
        # set a preset type if given
        if isinstance(preset_type, str):
            self.filter_type_box.setCurrentIndex(self.filter_type.index(preset_type))
        # add tooltip for every type option
        for i, tt in enumerate(self.filter_types[self.column_type + "_tt"]):
            self.filter_type_box.setItemData(i, tt, Qt.ToolTipRole)

        # create the filter input line
        self.filter_query_line = QtWidgets.QLineEdit()
        self.filter_query_line.setFocusPolicy(Qt.StrongFocus)

        if remove_option:
            # add buttons to remove the row
            self.remove = QtWidgets.QToolButton()
            self.remove.setIcon(qicons.delete)
            self.remove.setToolTip("Remove this filter")
            self.remove.clicked.connect(self.self_destruct)

    @property
    def get_state(self) -> tuple:
        raise NotImplementedError

    def set_state(self, state: tuple) -> None:
        raise NotImplementedError

    def set_input_changes(self) -> None:
        raise NotImplementedError

    def self_destruct(self) -> None:
        """Remove this FilterRow object from parent."""
        self.parent.remove_row(self.idx)


class StrFilterRow(FilterRow):
    """Convenience class for managing a filter input row for 'str' type."""

    def __init__(
        self,
        idx: int,
        filter_types: dict,
        state: tuple = None,
        remove_option: bool = True,
        preset_type: str = None,
        parent=None,
    ):

        self.column_type = "str"
        super().__init__(idx, filter_types, remove_option, preset_type, parent)

        # create case-sensitive box
        self.case_sensitive_text = QtWidgets.QLabel("Case Sensitive:")
        self.filter_case_sensitive_check = QtWidgets.QCheckBox()

        # assemble the layout
        self.row_layout.addWidget(self.filter_type_box)
        self.row_layout.addWidget(self.filter_query_line)
        self.row_layout.addWidget(self.case_sensitive_text)
        self.row_layout.addWidget(self.filter_case_sensitive_check)
        if remove_option:
            # add button to remove the row
            self.row_layout.addWidget(vertical_line())
            self.row_layout.addWidget(self.remove)

        self.setLayout(self.row_layout)

        # set the state if one was given
        if isinstance(state, tuple):
            self.set_state(state)

        self.filter_type_box.currentIndexChanged.connect(self.set_input_changes)
        self.set_input_changes()

    @property
    def get_state(self) -> tuple:
        # remove weird whitespace from input
        query_line = (
            self.filter_query_line.text()
            .translate(str.maketrans("", "", "\n\t\r"))
            .strip()
        )
        # if valid, return a tuple with the state, otherwise, return None
        if query_line == "":
            return None

        selected_type = self.filter_type_box.currentText()
        selected_query = self.filter_query_line.text()
        case_sensitive = self.filter_case_sensitive_check.isChecked()
        return selected_type, selected_query, case_sensitive

    def set_state(self, state: tuple) -> None:
        selected_type, selected_query, case_sensitive = state
        self.filter_type_box.setCurrentIndex(self.filter_type.index(selected_type))
        self.filter_query_line.setText(selected_query)
        self.filter_case_sensitive_check.setChecked(case_sensitive)

    def set_input_changes(self) -> None:
        # set tooltip to currently selected item
        tt = self.filter_types[self.column_type + "_tt"][
            self.filter_type_box.currentIndex()
        ]
        self.filter_type_box.setToolTip(tt)


class NumFilterRow(FilterRow):
    """Convenience class for managing a filter input row for 'num' type."""

    def __init__(
        self,
        idx: int,
        filter_types: dict,
        state: tuple = None,
        remove_option: bool = True,
        preset_type: str = None,
        parent=None,
    ):

        self.column_type = "num"
        super().__init__(idx, filter_types, remove_option, preset_type, parent)

        # add an input line in case 'between' ('<= x <=') is selected
        self.filter_query_line0 = QtWidgets.QLineEdit()
        self.filter_query_line0.hide()

        # set 'double' validator for input lines
        self.filter_query_line0.setValidator(QtGui.QDoubleValidator())
        self.filter_query_line.setValidator(QtGui.QDoubleValidator())

        # assemble the layout
        self.row_layout.addWidget(self.filter_query_line0)
        self.row_layout.addWidget(self.filter_type_box)
        self.row_layout.addWidget(self.filter_query_line)
        if remove_option:
            # add button to remove the row
            self.row_layout.addWidget(vertical_line())
            self.row_layout.addWidget(self.remove)

        self.setLayout(self.row_layout)

        # set the state if one was given
        if isinstance(state, tuple):
            self.set_state(state)

        self.filter_type_box.currentIndexChanged.connect(self.set_input_changes)
        self.set_input_changes()

    @property
    def get_state(self) -> tuple:
        # remove weird whitespace from input
        query_line = (
            self.filter_query_line.text()
            .translate(str.maketrans("", "", " \n\t\r"))
            .strip()
        )
        # if valid, return a tuple with the state, otherwise, return None
        if query_line == "":
            return None

        selected_type = self.filter_type_box.currentText()
        selected_query = self.filter_query_line.text()
        if self.filter_type_box.currentText() == "<= x <=":
            selected_query = (
                self.filter_query_line0.text(),
                self.filter_query_line.text(),
            )
        return selected_type, selected_query

    def set_state(self, state: tuple) -> None:
        selected_type, selected_query = state
        self.set_input_changes()
        self.filter_type_box.setCurrentIndex(self.filter_type.index(selected_type))
        if selected_type == "<= x <=":
            self.filter_query_line0.setText(selected_query[0])
            self.filter_query_line.setText(selected_query[1])
        else:
            self.filter_query_line.setText(selected_query)

    def set_input_changes(self) -> None:
        # enable whether the extra input line is visible
        if self.filter_type_box.currentText() == "<= x <=":
            self.filter_query_line0.show()
        else:
            self.filter_query_line0.hide()
        # set tooltip to currently selected item
        tt = self.filter_types[self.column_type + "_tt"][
            self.filter_type_box.currentIndex()
        ]
        self.filter_type_box.setToolTip(tt)



class SimpleFilterDialog(QtWidgets.QDialog):
    """Add one filter to a column.

    Related to FilterManagerDialog.
    """

    def __init__(
        self,
        column_name: dict,
        filter_types: dict,
        column_type: str = "str",
        preset_type: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowIcon(qicons.filter)
        self.setWindowTitle("Add filter")

        # Create filter label and buttons
        label = QtWidgets.QLabel("Define a filter for column '{}'".format(column_name))

        if column_type == "num":
            self.filter_row = NumFilterRow(
                idx=0,
                filter_types=filter_types,
                remove_option=False,
                preset_type=preset_type,
                parent=self,
            )
        else:
            # if none of the above types, assume str
            self.filter_row = StrFilterRow(
                idx=0,
                filter_types=filter_types,
                remove_option=False,
                preset_type=preset_type,
                parent=self,
            )

        self.filter_row.filter_query_line.setFocus()

        # create OK/cancel buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.filter_row)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def get_filter(self) -> tuple:
        if self.filter_row.get_state:
            return self.filter_row.get_state


class FilterManagerDialog(QtWidgets.QDialog):
    """Set filters for a table.

    Dialog has 1 tab per given column. Each tab has rows for filters,
    where type/query/other is defined. User can add/remove filters as desired.
    When multiple filters exist for 1 column, user can choose AND/OR combination of filters.
    AND/OR for combining columns can also be chosen.

    Required inputs:
    - column names: dict --> the column names and their indices in the table
        format: {'col_name': i}
    Optional inputs:
    - filters: dict --> pre-apply filters in the dialog (see format example below)
    - selected_column: int --> open the dialog with this column tab open
    - column_types: dict --> show other filters for this column
        format: {'col_name': 'num'}
        options: str/num, defaults to str if no type is given

    Interaction:
    - call 'start_filter_dialog' of 'ABFilterableDataFrameView' to launch dialog,
    filters are only applied when OK is selected. This calls self.get_filters,
    which returns filter data as dict.

    example of filters (see also ABMultiColumnSortProxyModel):
    filters = {
            0: {'filters': [('contains', 'heat', False), ('contains', 'electricity', False)],
                'mode': 'OR'},
            1: {'filters': [('contains', 'market', False)]}
        }
    """

    def __init__(
        self,
        column_names: dict,
        filter_types: dict,
        filters: dict = None,
        selected_column: int = 0,
        column_types: dict = {},
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowIcon(qicons.filter)
        self.setWindowTitle("Manage table filters")

        # set given filters, if any
        if isinstance(filters, dict):
            self.filters = filters
        else:
            self.filters = {}

        # create a tab for every column in the table
        self.tab_widget = QtWidgets.QTabWidget()
        self.tabs = []

        # we need this dict as we may have hidden columns (e.g. CFTable)
        self.col_id_2_tab_id = {}
        for tab_id, col_data in enumerate(column_names.items()):
            col_name, col_id = col_data
            self.col_id_2_tab_id[col_id] = tab_id
            tab = ColumnFilterTab(
                parent=self,
                state=self.filters.get(col_id, None),
                col_type=column_types.get(col_name, "str"),
                filter_types=filter_types,
            )
            self.tabs.append(tab)
            self.tab_widget.addTab(tab, col_name)

        # add AND/OR choice button.
        self.and_or_buttons = AndOrRadioButtons(label_text="Combine columns:")
        # in the extremely unlikely event there is only 1 column, hide the AND/OR option.
        if len(column_names) == 1:
            self.and_or_buttons.hide()

        # create OK/cancel buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # assemble layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.and_or_buttons)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

        # set the column that launched the dialog as the open tab
        self.tab_widget.setCurrentIndex(self.col_id_2_tab_id[selected_column])
        self.tabs[selected_column].filter_rows[-1].filter_query_line.setFocus()

    @property
    def get_filters(self) -> dict:
        state = {}
        t2c = {v: k for k, v in self.col_id_2_tab_id.items()}
        for tab_id, tab in enumerate(self.tabs):
            tab_state = tab.get_state
            if isinstance(tab_state, dict):
                state[t2c[tab_id]] = tab_state
        if len(state) == 0:
            return
        state["mode"] = self.and_or_buttons.get_state
        return state


