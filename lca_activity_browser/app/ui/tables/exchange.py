# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from ..icons import icons
from .activity import ActivityItem, ActivitiesTableWidget
from .biosphere import FlowsTableWidget
from PyQt4 import QtCore, QtGui


class Reference(QtGui.QTableWidgetItem):
    def __init__(self, *args, exchange=None, direction="down"):
        super(Reference, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.exchange = exchange
        self.direction = direction


class Amount(QtGui.QTableWidgetItem):
    def __init__(self, *args, exchange=None):
        super(Amount, self).__init__(*args)
        # self.setFlags(self.flags() & QtCore.Qt.ItemIsEditable)
        self.exchange = exchange
        self.previous = self.text()


class ReadOnly(QtGui.QTableWidgetItem):
    def __init__(self, *args):
        super(ReadOnly, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)


class ExchangeTableWidget(QtGui.QTableWidget):
    COLUMN_LABELS = {
        (False, False): ["Activity", "Product", "Amount", "Uncertain", "Unit"],
        (True, False): ["Name", "Categories", "Amount", "Uncertain", "Unit"],
        (False, True): ["Product", "Amount", "Uncertain", "Unit"],
    }

    def __init__(self, parent, biosphere=False, production=False):
        super(ExchangeTableWidget, self).__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.biosphere = biosphere
        self.production = production
        self.column_labels = self.COLUMN_LABELS[(biosphere, production)]
        self.setColumnCount(len(self.column_labels))
        self.qs, self.upstream, self.database = None, False, None
        self.ignore_changes = False

        self.delete_exchange_action = QtGui.QAction(
            QtGui.QIcon(icons.delete), "Delete exchange(s)", None
        )
        self.addAction(self.delete_exchange_action)
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)

        self.cellChanged.connect(self.filter_amount_change)
        self.cellDoubleClicked.connect(self.filter_clicks)
        signals.database_changed.connect(self.filter_database_changed)

    def delete_exchanges(self, event):
        signals.exchanges_deleted.emit(
            [x.exchange for x in self.selectedItems()]
        )

    def dragEnterEvent(self, event):
        acceptable = (
            ActivitiesTableWidget,
            ExchangeTableWidget,
            FlowsTableWidget,
        )
        if isinstance(event.source(), acceptable):
            event.accept()

    def dropEvent(self, event):
        items = event.source().selectedItems()
        if isinstance(items[0], ActivityItem):
            signals.exchanges_add.emit([x.key for x in items], self.qs._key)
        else:
            signals.exchanges_output_modified.emit(
                [x.exchange for x in items], self.qs._key
            )
        event.accept()

    def filter_database_changed(self, database):
        if self.database == database:
            self.sync()

    def filter_amount_change(self, row, col):
        if not col == 2 or self.ignore_changes:
            return
        try:
            item = self.item(row, col)
            if item.text() == item.previous:
                return
            else:
                item.previous = item.text()
            value = float(item.text())
            exchange = item.exchange
            signals.exchange_amount_modified.emit(exchange, value)
        except:
            # TODO: Handle error here...
            pass

    def filter_clicks(self, row, col):
        if self.biosphere or self.production or col != 0:
            return
        item = self.item(row, col)
        key = (
            item.exchange.input.key
            if item.direction == "down"
            else item.exchange.output.key
        )
        if self.upstream:
            signals.open_activity_tab.emit("left", item.exchange['output'])
        else:
            signals.open_activity_tab.emit("left", item.exchange['input'])

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

            self.setItem(
                row,
                0,
                Reference(
                    obj['name'],
                    exchange=exc,
                    direction=direction
                )
            )
            if self.production:
                self.setItem(
                    row,
                    1,
                    Amount(
                        "{:.4g}".format(exc['amount']),
                        exchange=exc
                    )
                )
                self.setItem(
                    row,
                    2,
                    ReadOnly("True" if exc.get("uncertainty type", 0) > 1 else "False")
                )
                self.setItem(row, 3, ReadOnly(obj.get('unit', 'Unknown')))
            else:
                if self.biosphere:
                    self.setItem(row, 1, ReadOnly(" - ".join(obj.get('categories', []))))
                else:
                    self.setItem(
                        row,
                        1,
                        Reference(
                            obj.get('reference product') or obj["name"],
                            exchange=exc,
                            direction=direction
                        )
                    )
                self.setItem(
                    row,
                    2,
                    Amount(
                        "{:.4g}".format(exc['amount']),
                        exchange=exc
                    )
                )
                self.setItem(
                    row,
                    3,
                    ReadOnly("True" if exc.get("uncertainty type", 0) > 1 else "False")
                )
                self.setItem(row, 4, ReadOnly(obj.get('unit', 'Unknown')))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.ignore_changes = False
