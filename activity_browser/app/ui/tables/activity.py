# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .inventory import ActivitiesTable
from .inventory import BiosphereFlowsTable
from .table import ABTableWidget, ABTableItem
from ..icons import icons
from ...signals import signals


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
    """
    COLUMN_LABELS = {  # {exchangeTableName: headers}
        "products": ["Amount", "Unit", "Output Name", "Location"],
        # todo(?) should the table functionality for downstream activities really be identical to technosphere inputs?
        # technosphere inputs & Downstream product-consuming activities that consume the
        "technosphere": ["Amount", "Unit", "Input Name", "Location", "Uncertainty", "Product DB"],
        "biosphere": ["Amount", "Unit", "Flow Name", "Compartments", "Uncertainty", "Flow DB"],
    }
    def __init__(self, parent, tableType):
        super(ExchangeTable, self).__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)

        self.tableType = tableType
        self.column_labels = self.COLUMN_LABELS[self.tableType]
        self.setColumnCount(len(self.column_labels))
        # default values, updated later in set_queryset()
        self.qs, self.upstream, self.database = None, False, None
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
        signals.database_changed.connect(self.filter_database_changed)
        self.cellChanged.connect(self.filter_amount_change)
        self.cellDoubleClicked.connect(self.filter_clicks)

    def delete_exchanges(self, event):
        signals.exchanges_deleted.emit(
            [x.exchange for x in self.selectedItems()]
        )

    def dragEnterEvent(self, event):
        acceptable = (
            ActivitiesTable,
            ExchangeTable,
            BiosphereFlowsTable,
        )
        if isinstance(event.source(), acceptable):
            event.accept()

    def dropEvent(self, event):
        items = event.source().selectedItems()
        if isinstance(items[0], ABTableItem):
            signals.exchanges_add.emit([x.key for x in items], self.qs._key)
        else:
            print(items)
            print(items.exchange)
            signals.exchanges_output_modified.emit(
                [x.exchange for x in items], self.qs._key
            )
        event.accept()

    def filter_database_changed(self, database):
        if self.database == database:
            self.sync()

    def filter_amount_change(self, row, col):
        try:
            item = self.item(row, col)
            if self.ignore_changes:
                return
            elif item.text() == item.previous:
                return
            else:
                value = float(item.text())
                item.previous = item.text()
                exchange = item.exchange
                signals.exchange_amount_modified.emit(exchange, value)
        except ValueError:
            print('You can only enter numbers here.')
            item.setText(item.previous)

    def filter_clicks(self, row, col):
        item = self.item(row, col)
        # todo(?): series of ORs seems overly inclusive - intended purpose unclear
        if self.tableType == "products" or self.tableType == "biosphere" or (item.flags() & QtCore.Qt.ItemIsEditable):
            return

        if hasattr(item, "exchange"):
            if self.upstream:
                key = item.exchange['output']
            else:
                key = item.exchange['input']
            signals.open_activity_tab.emit("activities", key)
            signals.add_activity_to_history.emit(key)

    def set_queryset(self, database, qs, limit=100, upstream=False):
        # todo(?): as this function calls sync() - it appears to do more than just setting the queryset
        # ...purpose of calling this function (in ActivityTab) would be clearer if renamed
        self.database, self.qs, self.upstream = database, qs, upstream
        self.sync(limit)

    @ABTableWidget.decorated_sync
    def sync(self, limit=100):
        self.ignore_changes = True
        self.setRowCount(min(len(self.qs), limit))
        self.setHorizontalHeaderLabels(self.column_labels)

        if self.upstream:
            # todo(?): move to init
            self.setDragEnabled(False)
            self.setAcceptDrops(False)

        # edit_flag is passed to table items which should be user-editable.
        # Default flag for cells is uneditable - which still allows cell-selection/highlight
        edit_flag = [QtCore.Qt.ItemIsEditable]

        # todo: add a setting which allows user to choose their preferred number formatting, for use in tables
        # e.g. a choice between all standard form: {0:.3e} and current choice: {:.3g}. Or more flexibility
        for row, exc in enumerate(self.qs):
            act = exc.output if self.upstream else exc.input
            if row == limit:
                # todo: use table paging rather than a hard limit
                break

            if self.tableType == "products":  # "Amount", "Unit", "Name", "Location"
                self.setItem(row, 0, ABTableItem(
                    "{:.3g}".format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    act.get('unit', 'Unknown'), color="unit"))

                self.setItem(row, 2, ABTableItem(
                    # correct reference product name is stored in the exchange itself and not the activity
                    act.get('reference product') or act.get("name") if self.upstream else
                    exc.get('reference product') or exc.get("name"),
                    exchange=exc, color="reference product"))

                self.setItem(row, 4, ABTableItem(
                    act.get('location', 'Unknown'), color="location"))

            elif self.tableType == "technosphere":  # "Amount","Unit","Product","Location","Uncertainty","Product db"
                self.setItem(row, 0, ABTableItem(
                    "{:.3g}".format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    act.get('unit', 'Unknown'), color="unit"))

                self.setItem(row, 2, ABTableItem(
                    # correct reference product name is stored in the exchange itself, not the activity
                    # todo: clarify and document what this code does
                    act.get('reference product') or act.get("name") if self.upstream else
                    exc.get('reference product') or exc.get("name"),
                    exchange=exc, color="reference product"))

                self.setItem(row, 3, ABTableItem(
                    exc.get('location', 'Unknown'), color="location"))

                self.setItem(row, 4, ABTableItem(
                    str(exc.get("uncertainty type", ""))))

                # todo: can exchanges be in a different db to the activity?
                self.setItem(row, 5, ABTableItem(
                    exc.get('database'), color="database"))

            elif self.tableType == "biosphere":  # "Amount", "Unit", "Name", "Compartments", "Uncertainty", "Database"
                self.setItem(row, 0, ABTableItem(
                    "{:.3g}".format(exc.get('amount')), exchange=exc, set_flags=edit_flag, color="amount"))

                self.setItem(row, 1, ABTableItem(
                    act.get('unit', 'Unknown'), color="unit"))

                self.setItem(row, 2, ABTableItem(
                    act.get('name'), exchange=exc, color="name"))

                self.setItem(row, 3, ABTableItem(
                    " - ".join(act.get('categories', [])), color="categories"))

                self.setItem(row, 4, ABTableItem(
                    str(exc.get("uncertainty type", ""))))

                self.setItem(row, 5, ABTableItem(
                    act.get('database'), color="database"))

        self.ignore_changes = False
