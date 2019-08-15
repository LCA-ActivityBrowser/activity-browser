# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .inventory import ActivitiesBiosphereTable
from .table import ABTableWidget, ABTableItem
from ..icons import icons
from ...signals import signals
from ...bwutils.commontasks import AB_names_to_bw_keys, bw_keys_to_AB_names


class ExchangeTable(ABTableWidget):
    """ All tables shown in the ActivityTab are instances of this class (inc. non-exchange types)
    Differing Views and Behaviours of tables are handled based on their tableType
    todo(?): possibly preferable to subclass for distinct table functionality, rather than conditionals in one class
    The tables include functionalities: drag-drop, context menus, in-line value editing
    The read-only/editable status of tables is handled in ActivityTab.set_exchange_tables_read_only()
    Instantiated with headers but without row-data
    Then set_queryset() called from ActivityTab with params
    set_queryset calls Sync() to fill and format table data items
    todo(?): the variables which are initiated as defaults then later populated in set_queryset() can be passed at init
       Therefore this class could be simplified by removing self.qs,upstream,database defaults etc.
    todo(?): column names determined by properties included in the activity and exchange?
        this would mean less hard-coding of column titles and behaviour. But rather dynamic generation
        and flexible editing based on assumptions about data types etc.
    """
    COLUMN_LABELS = {  # {exchangeTableName: headers}
        "products": ["Amount", "Unit", "Product", "Formula"], #, "Location", "Uncertainty"],
        # technosphere inputs & Downstream product-consuming activities included as "technosphere"
        # todo(?) should the table functionality for downstream activities really be identical to technosphere inputs?
        "technosphere": ["Amount", "Unit", "Product", "Activity", "Location", "Database", "Uncertainty", "Formula"],
        "biosphere": ["Amount", "Unit", "Flow Name", "Compartments", "Database", "Uncertainty", "Formula"],
    }
    def __init__(self, parent=None, tableType=None):
        super(ExchangeTable, self).__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSortingEnabled(True)

        self.tableType = tableType
        self.column_labels = self.COLUMN_LABELS[self.tableType]
        self.setColumnCount(len(self.column_labels))
        # default values, updated later in set_queryset()
        self.qs, self.downstream, self.database = None, False, None
        # ignore_changes set to True whilst sync() executes to prevent conflicts(?)
        self.ignore_changes = False
        self.setup_context_menu()
        self.connect_signals()
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def setup_context_menu(self):
        # todo: different table types require different context menu actions
        self.delete_exchange_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete exchange(s)", None
        )
        self.addAction(self.delete_exchange_action)
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)

    def connect_signals(self):
        # todo: different table types require different signals connected
        signals.database_changed.connect(self.update_when_database_has_changed)
        self.cellChanged.connect(self.filter_change)
        self.cellDoubleClicked.connect(self.handle_double_clicks)

    def delete_exchanges(self, event):
        signals.exchanges_deleted.emit(
            [x.exchange for x in self.selectedItems()]
        )

    def dragEnterEvent(self, event):
        acceptable = (
            ExchangeTable,
            ActivitiesBiosphereTable,
        )
        if isinstance(event.source(), acceptable):
            event.accept()

    def dropEvent(self, event):
        source_table = event.source()
        print('Dropevent from:', source_table)
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        signals.exchanges_add.emit(keys, self.qs._key)

        # items = event.source().selectedItems()
        # if isinstance(items[0], ABTableItem):
        #     signals.exchanges_add.emit([x.key for x in items], self.qs._key)
        # else:
        #     print(items)
        #     print(items.exchange)
        #     signals.exchanges_output_modified.emit(
        #         [x.exchange for x in items], self.qs._key
        #     )
        event.accept()

    def update_when_database_has_changed(self, database):
        if self.database == database:
            self.sync()

    def filter_change(self, row, col):
        """ Take inputs from the user and edit the relevant parts of the
         database.

         There are currently four possible editable fields:
         Amount, Unit, Product and Formula
         """
        item = self.item(row, col)
        if self.ignore_changes:  # todo: check or remove
            return
        elif item.text() == item.previous:
            return
        field_name = AB_names_to_bw_keys[self.COLUMN_LABELS[self.tableType][col]]

        if field_name == "amount":
            try:
                value = float(item.text())
            except ValueError:
                print('You can only enter numbers here.')
                item.setText(item.previous)
                return
        else:
            value = str(item.text())
        item.previous = item.text()

        if field_name in ["amount", "formula"]:
            exchange = item.exchange
            signals.exchange_modified.emit(exchange, field_name, value)
        else:
            act_key = item.exchange.output.key
            signals.activity_modified.emit(act_key, field_name, value)

    def handle_double_clicks(self, row, col):
        """ handles double-click events rather than clicks... rename? """
        item = self.item(row, col)
        print("double-clicked on:", row, col, item.text())
        # double clicks ignored for these table types and item flags (until an 'exchange edit' interface is written)
        if self.tableType == "products" or self.tableType == "biosphere" or (item.flags() & QtCore.Qt.ItemIsEditable):
            return

        if hasattr(item, "exchange"):
            # open the activity of the row which was double clicked in the table
            if self.upstream:
                key = item.exchange['output']
            else:
                key = item.exchange['input']
            signals.open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    def set_queryset(self, database, qs, limit=100, downstream=False):
        # todo(?): rename function: it calls sync() - which appears to do more than just setting the queryset
        # todo: use table paging rather than a hard arbitrary 'limit'. Could also increase load speed
        #  .upstream() exposes the exchanges which consume this activity.
        self.database, self.qs, self.upstream = database, qs, downstream
        self.sync(limit)

    @ABTableWidget.decorated_sync
    def sync(self, limit=100):
        """ populates an exchange table view with data about the exchanges, bios flows, and adjacent activities """
        self.ignore_changes = True
        self.setRowCount(min(len(self.qs), limit))
        self.setHorizontalHeaderLabels(self.column_labels)

        if self.upstream:
            # ideally these should not be set in the data syncing function
            # todo: refactor so that on initialisation, the 'upstream' state is known so state can be set there
            self.setDragEnabled(False)
            self.setAcceptDrops(False)
            # 'upstream' means downstream, hide the 'formula' column for this table
            self.setColumnHidden(7, True)

        # edit_flag is passed to table items which should be user-editable.
        # Default flag for cells is uneditable - which still allows cell-selection/highlight
        edit_flag = [QtCore.Qt.ItemIsEditable]

        # todo: add a setting which allows user to choose their preferred number formatting, for use in tables
        # e.g. a choice between all standard form: {0:.3e} and current choice: {:.3g}. Or more flexibility
        amount_format_string = "{:.3g}"
        for row, exc in enumerate(self.qs):
            # adj_act is not the open activity, but rather one of the activities connected adjacently via an exchange
            # When open activity is upstream of the two...
            # The adjacent activity we want to view is the output of the exchange which connects them. And vice versa
            adj_act = exc.output if self.upstream else exc.input
            if row == limit:

                break

            if self.tableType == "products":
                # headers: "Amount", "Unit", "Product", "Location", "Uncertainty"
                self.setItem(row, 0, ABTableItem(
                    amount_format_string.format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    adj_act.get('unit', 'Unknown'), exchange=exc, set_flags=edit_flag, color="unit"))

                self.setItem(row, 2, ABTableItem(
                    # correct reference product name is stored in the exchange itself and not the activity
                    # adj_act.get('reference product') or adj_act.get("name") if self.upstream else
                    adj_act.get('reference product') or adj_act.get("name"),
                    exchange=exc, set_flags=edit_flag, color="reference product"))

                self.setItem(row, 3, ABTableItem(
                    exc.get("formula", ""), exchange=exc, set_flags=edit_flag))

                # self.setItem(row, 3, ABTableItem(
                #     # todo: remove? it makes no sense to show the (open) activity location...
                #     # showing exc locations (as now) makes sense. But they rarely have one...
                #     # I believe they usually implicitly inherit the location of the producing activity
                #     str(exc.get('location', '')), color="location"))

                # # todo: can both outputs and inputs of a process both have uncertainty data?
                # self.setItem(row, 3, ABTableItem(
                #     str(exc.get("uncertainty type", ""))))

            elif self.tableType == "technosphere":
                # headers: "Amount", "Unit", "Product", "Activity", "Location", "Database", "Uncertainty", "Formula"

                self.setItem(row, 0, ABTableItem(
                    amount_format_string.format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    adj_act.get('unit', 'Unknown'), exchange=exc, color="unit"))

                self.setItem(row, 2, ABTableItem(  # product
                    # if statement used to show different activities for products and downstream consumers tables
                    # reference product shown, and if absent, just the name of the activity or exchange...
                    # would this produce inconsistent/unclear behaviour for users?
                    adj_act.get('reference product') or adj_act.get("name") if self.upstream else
                    exc.get('reference product') or exc.get("name"),
                    exchange=exc, color="reference product"))

                self.setItem(row, 3, ABTableItem(  # name of adjacent activity (up or downstream depending on table)
                    adj_act.get('name'), exchange=exc, color="name"))

                self.setItem(row, 4, ABTableItem(
                    str(adj_act.get('location', '')), exchange=exc, color="location"))

                self.setItem(row, 5, ABTableItem(
                    adj_act.get('database'), exchange=exc, color="database"))

                self.setItem(row, 6, ABTableItem(
                    str(exc.get("uncertainty type", "")), exchange=exc,))

                self.setItem(row, 7, ABTableItem(
                    exc.get('formula', ''), exchange=exc, set_flags=edit_flag))

            elif self.tableType == "biosphere":
                # headers: "Amount", "Unit", "Flow Name", "Compartments", "Database", "Uncertainty"
                self.setItem(row, 0, ABTableItem(
                    amount_format_string.format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    adj_act.get('unit', 'Unknown'), exchange=exc, color="unit"))

                self.setItem(row, 2, ABTableItem(
                    adj_act.get('name'), exchange=exc, color="product"))

                self.setItem(row, 3, ABTableItem(
                    " - ".join(adj_act.get('categories', [])), exchange=exc, color="categories"))

                self.setItem(row, 4, ABTableItem(
                    adj_act.get('database'), exchange=exc, color="database"))

                self.setItem(row, 5, ABTableItem(
                    str(exc.get("uncertainty type", "")), exchange=exc))

                # Yes, _exchanges_ can have both a formula and an amount, if the activity is parameterized,
                # the formula is used to calculate the amount of that specific exchange on save.
                # If the activity is not parameterized, the formula can be set but is not used
                # to calculate the amount.
                # See: https://docs.brightwaylca.org/intro.html#active-versus-passive-parameters
                self.setItem(row, 6, ABTableItem(
                    exc.get("formula", ""), exchange=exc, set_flags=edit_flag))
        self.ignore_changes = False


# start of a simplified way to handle these tables...

class ExchangesTablePrototype(ABTableWidget):
    amount_format_string = "{:.3g}"


    def __init__(self, parent=None):
        super(ExchangesTablePrototype, self).__init__()
        self.column_labels = [bw_keys_to_AB_names[val] for val in self.COLUMNS.values()]
        self.setColumnCount(len(self.column_labels))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

    def set_queryset(self, database, qs, limit=100, upstream=False):
        self.database, self.qs, self.upstream = database, qs, upstream
        # print("Queryset:", self.database, self.qs, self.upstream)
        self.sync(limit)
