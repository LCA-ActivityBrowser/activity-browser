# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .inventory import ActivitiesTable
from .inventory import BiosphereFlowsTable
from .table import ABTableWidget, ABTableItem
from ..icons import icons
from ...signals import signals


class ExchangeTable(ABTableWidget):
    COLUMN_LABELS = {
        # Products
        (False, True): ["Amount", "Unit", "Product", "Activity",
                        "Location", "Database", "Uncertain"],
        # technosphere & downstream consumers
        (False, False): ["Amount", "Unit", "Product", "Activity",
                         "Location", "Database", "Uncertain", "Formula"],
        # Biosphere
        (True, False): ["Amount", "Unit", "Name", "Categories", "Database", "Uncertain"],
    }

    def __init__(self, parent, biosphere=False, production=False):
        super(ExchangeTable, self).__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)
        self.biosphere = biosphere
        self.production = production
        self.column_labels = self.COLUMN_LABELS[(biosphere, production)]
        self.setColumnCount(len(self.column_labels))
        self.qs, self.upstream, self.database = None, False, None
        self.ignore_changes = False
        self.setup_context_menu()
        self.connect_signals()
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )


    def setup_context_menu(self):
        self.delete_exchange_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete exchange(s)", None
        )
        self.addAction(self.delete_exchange_action)
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)

    def connect_signals(self):
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
        if self.biosphere or self.production or (item.flags() & QtCore.Qt.ItemIsEditable):
            return

        if hasattr(item, "exchange"):
            if self.upstream:
                key = item.exchange['output']
            else:
                key = item.exchange['input']
            signals.open_activity_tab.emit("activities", key)
            signals.add_activity_to_history.emit(key)

    def set_queryset(self, database, qs, limit=100, upstream=False):
        self.database, self.qs, self.upstream = database, qs, upstream
        self.sync(limit)

    @ABTableWidget.decorated_sync
    def sync(self, limit=100):
        self.ignore_changes = True
        self.setRowCount(min(len(self.qs), limit))
        self.setHorizontalHeaderLabels(self.column_labels)

        if self.upstream:
            self.setDragEnabled(False)
            self.setAcceptDrops(False)

        for row, exc in enumerate(self.qs):
            act = exc.output if self.upstream else exc.input
            if row == limit:
                # todo: use table paging rather than a hard limit
                break

            edit_flag = [QtCore.Qt.ItemIsEditable]

            if self.biosphere:  #"Amount", "Unit", "Name", "Categories", "Database", "Uncertain"
                self.setItem(row, 0, ABTableItem("{:.4g}".format(exc.get('amount')), exchange=exc,
                                                 set_flags=edit_flag, color="amount"))
                self.setItem(row, 1, ABTableItem(act.get('unit', 'Unknown'), color="unit"))
                self.setItem(row, 2, ABTableItem(
                    act.get('name'), exchange=exc, color="name"
                ))
                self.setItem(row, 3, ABTableItem(
                    " - ".join(act.get('categories', [])), color="categories"
                ))
                self.setItem(row, 4, ABTableItem(act.get('database'), color="database"))
                self.setItem(row, 5, ABTableItem(
                    "True" if exc.get("uncertainty type", 0) > 1 else "False"
                ))

            else:  # ["Amount", "Unit", "Product", "Activity", "Location", "Database", "Uncertain", "Formula"]
                self.setItem(row, 0, ABTableItem("{:.4g}".format(exc.get('amount')), exchange=exc,
                                                 set_flags=edit_flag, color="amount"))
                self.setItem(row, 1, ABTableItem(act.get('unit', 'Unknown'), color="unit"))
                self.setItem(row, 2, ABTableItem(
                    act.get('reference product') or act.get("name") if self.upstream else
                    exc.get('reference product') or exc.get("name"),  # correct reference product name is stored in the exchange itself and not the activity
                    exchange=exc, color="reference product"
                ))
                self.setItem(row, 3, ABTableItem(
                    act.get('name'), exchange=exc, color="name")
                )
                self.setItem(row, 4, ABTableItem(act.get('location', 'Unknown'), color="location"))
                self.setItem(row, 5, ABTableItem(act.get('database'), color="database"))
                self.setItem(row, 6, ABTableItem(
                    "True" if exc.get("uncertainty type", 0) > 1 else "False")
                )
                self.setItem(row, 7, ABTableItem(exc.get('formula', '')))

        self.ignore_changes = False
