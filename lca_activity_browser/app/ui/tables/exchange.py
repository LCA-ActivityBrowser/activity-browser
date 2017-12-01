# -*- coding: utf-8 -*-
from ...signals import signals
from ..icons import icons
from .activity import ActivityItem, ActivitiesTableWidget
from .biosphere import FlowsTableWidget
from PyQt5 import QtCore, QtGui, QtWidgets


class Reference(QtWidgets.QTableWidgetItem):
    def __init__(self, exchange, direction, *args):
        super(Reference, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.exchange = exchange
        self.direction = direction


class Amount(QtWidgets.QTableWidgetItem):
    def __init__(self, exchange, *args):
        super(Amount, self).__init__(*args)
        # self.setFlags(self.flags() & QtCore.Qt.ItemIsEditable)
        self.exchange = exchange
        self.previous = self.text()


class ReadOnly(QtWidgets.QTableWidgetItem):
    def __init__(self, *args):
        super(ReadOnly, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)


class ExchangeTableWidget(QtWidgets.QTableWidget):
    COLUMN_LABELS = {
        # Normal technosphere
        (False, False): ["Activity", "Product", "Amount", "Database",
                         "Location", "Unit", "Uncertain"],
        # Biosphere
        (True, False): ["Name", "Amount", "Unit", "Database", "Categories", "Uncertain"],
        # Production
        (False, True): ["Product", "Amount", "Unit", "Uncertain"],
    }

    def __init__(self, parent, biosphere=False, production=False):
        super(ExchangeTableWidget, self).__init__()
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

            if self.production:  # "Product", "Amount", "Unit", "Uncertain"
                self.setItem(
                    row,
                    0,
                    Reference(
                        exc,
                        direction,
                        obj['name'],
                    )
                )
                self.setItem(
                    row,
                    1,
                    Amount(
                        exc,
                        "{:.4g}".format(exc['amount']),
                    )
                )
                self.setItem(row, 2, ReadOnly(obj.get('unit', 'Unknown')))
                self.setItem(
                    row,
                    3,
                    ReadOnly("True" if exc.get("uncertainty type", 0) > 1 else "False")
                )
            elif self.biosphere:  # "Name", "Amount", "Unit", "Database", "Categories", "Uncertain"
                self.setItem(
                    row,
                    0,
                    Reference(
                        exc,
                        direction,
                        obj['name'],
                    )
                )
                self.setItem(
                    row,
                    1,
                    Amount(
                        exc,
                        "{:.4g}".format(exc['amount']),
                    )
                )
                self.setItem(row, 2, ReadOnly(obj.get('unit', 'Unknown')))
                self.setItem(row, 3, ReadOnly(obj['database']))
                self.setItem(row, 4, ReadOnly(" - ".join(obj.get('categories', []))))
                self.setItem(
                    row,
                    5,
                    ReadOnly("True" if exc.get("uncertainty type", 0) > 1 else "False")
                )
            else:  # "Activity", "Product", "Amount", "Database", "Location", "Unit", "Uncertain"
                self.setItem(
                    row,
                    0,
                    Reference(
                        exc,
                        direction,
                        obj['name'],
                    )
                )
                self.setItem(
                    row,
                    1,
                    Reference(
                        exc,
                        direction,
                        obj.get('reference product') or obj["name"],
                    )
                )
                self.setItem(
                    row,
                    2,
                    Amount(
                        exc,
                        "{:.4g}".format(exc['amount']),
                    )
                )
                self.setItem(row, 3, ReadOnly(obj['database']))
                self.setItem(row, 4, ReadOnly(obj.get('location', 'Unknown')))
                self.setItem(row, 5, ReadOnly(obj.get('unit', 'Unknown')))
                self.setItem(
                    row,
                    6,
                    ReadOnly("True" if exc.get("uncertainty type", 0) > 1 else "False")
                )

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.ignore_changes = False
