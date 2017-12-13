# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .activity import ActivitiesTable
from .biosphere import BiosphereFlowsTable
from .table import ABTableWidget, ABTableItem
from ..icons import icons
from ...signals import signals


class ExchangeTable(ABTableWidget):
    COLUMN_LABELS = {
        # Production
        (False, True): ["Activity", "Product", "Amount", "Database", "Location", "Unit", "Uncertain"],
        # Normal technosphere
        (False, False): ["Activity", "Product", "Amount", "Database", "Location", "Unit", "Uncertain"],
        # Biosphere
        (True, False): ["Name", "Amount", "Unit", "Database", "Categories", "Uncertain"],
    }

    def __init__(self, parent, biosphere=False, production=False):
        super(ExchangeTable, self).__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.biosphere = biosphere
        self.production = production
        self.column_labels = self.COLUMN_LABELS[(biosphere, production)]
        self.setColumnCount(len(self.column_labels))
        self.qs, self.upstream, self.database = None, False, None
        self.ignore_changes = False

        self.delete_exchange_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete exchange(s)", None
        )
        self.addAction(self.delete_exchange_action)
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)

        self.connect_signals()

    def connect_signals(self):
        # SIGNALS
        # TODO: these are not signals... check also in other places and make it consistent
        self.cellChanged.connect(self.filter_amount_change)
        self.cellDoubleClicked.connect(self.filter_clicks)
        # SLOTS
        signals.database_changed.connect(self.filter_database_changed)

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
        print('Double clicked on row/col {} {}'.format(row, col))
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

    def sync(self, limit=100):
        self.ignore_changes = True
        self.clear()
        self.setRowCount(min(len(self.qs), limit))
        self.setHorizontalHeaderLabels(self.column_labels)

        if self.upstream:
            self.setDragEnabled(False)
            self.setAcceptDrops(False)

        for row, exc in enumerate(self.qs):
            obj = exc.output if self.upstream else exc.input
            direction = "up" if self.upstream else "down"
            if row == limit:
                break

            # if self.production:
            #     flags = []
            # else:
            flags = [QtCore.Qt.ItemIsEditable]

            if self.biosphere:  # "Name", "Amount", "Unit", "Database", "Categories", "Uncertain"
                self.setItem(row, 0, ABTableItem(obj['name'], exchange=exc, direction=direction, ))
                self.setItem(row, 1, ABTableItem("{:.4g}".format(exc['amount']), exchange=exc, set_flags=flags))
                self.setItem(row, 2, ABTableItem(obj.get('unit', 'Unknown')))
                self.setItem(row, 3, ABTableItem(obj['database']))
                self.setItem(row, 4, ABTableItem(" - ".join(obj.get('categories', []))))
                self.setItem(row, 5, ABTableItem("True" if exc.get("uncertainty type", 0) > 1 else "False"))
            else:  # "Activity", "Product", "Amount", "Database", "Location", "Unit", "Uncertain"
                self.setItem(row, 0, ABTableItem(obj['name'], exchange=exc, direction=direction))
                self.setItem(row, 1, ABTableItem(obj.get('reference product') or obj["name"], exchange=exc, direction=direction, ))
                self.setItem(row, 2, ABTableItem("{:.4g}".format(exc['amount']), exchange=exc, set_flags=flags,))
                self.setItem(row, 3, ABTableItem(obj['database']))
                self.setItem(row, 4, ABTableItem(obj.get('location', 'Unknown')))
                self.setItem(row, 5, ABTableItem(obj.get('unit', 'Unknown')))
                self.setItem(row, 6, ABTableItem("True" if exc.get("uncertainty type", 0) > 1 else "False"))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        # make tables as small as possible
        if self.rowCount() > 0:
            self.setMaximumHeight(self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin())
        else:
            self.hide()
        self.ignore_changes = False
