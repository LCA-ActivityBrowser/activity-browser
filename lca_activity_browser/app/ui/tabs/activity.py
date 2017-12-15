# -*- coding: utf-8 -*-
import functools

import brightway2 as bw
from PyQt5 import QtCore, QtWidgets

from .. import header
from ..tables import ExchangeTable
from ..widgets import ActivityDataGrid


class ActivityDetailsTab(QtWidgets.QWidget):
    def __init__(self, parent=None, activity=None):
        super(ActivityDetailsTab, self).__init__(parent)
        self.parent = parent

        self.details_widget = self.get_details_widget()

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setAlignment(QtCore.Qt.AlignTop)
        vlayout.addWidget(self.details_widget)

        self.setLayout(vlayout)

        if activity:
            self.populate(activity)

    def toggle_visible(self, table):
        if table.state == "shown":
            table.state = "hidden"
            table.toggle_button.setText("Show")
            table.hide()
        else:
            table.state = "shown"
            table.show()
            table.toggle_button.setText("Hide")

    def get_details_widget(self):
        self.production = ExchangeTable(self, production=True)
        self.inputs = ExchangeTable(self)
        self.flows = ExchangeTable(self, biosphere=True)
        self.upstream = ExchangeTable(self)

        layout = QtWidgets.QVBoxLayout()
        self.metadata = ActivityDataGrid()
        layout.addWidget(self.metadata)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        tables = [
            (self.production, "Products:"),
            (self.inputs, "Technosphere Inputs:"),
            (self.flows, "Biosphere flows:"),
            (self.upstream, "Downstream consumers:"),
        ]

        for table, label in tables:
            table.state = "shown"
            table.toggle_button = QtWidgets.QPushButton("Hide")
            table.toggle_button.clicked.connect(functools.partial(self.toggle_visible, table=table))

            inside_widget = QtWidgets.QWidget()
            inside_layout = QtWidgets.QHBoxLayout()
            inside_layout.addWidget(header(label))
            inside_layout.addWidget(table.toggle_button)
            inside_layout.addStretch()
            inside_widget.setLayout(inside_layout)

            # layout.addWidget(inside_widget)
            # layout.addWidget(table)

            inside_widget.setSizePolicy(QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Maximum,
                QtWidgets.QSizePolicy.Maximum)
            )

            table.setSizePolicy(QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Preferred)
            )

            table_layout = QtWidgets.QVBoxLayout()
            table_layout.addWidget(inside_widget)
            table_layout.addWidget(table)
            table_container = QtWidgets.QWidget()



            table_container.setLayout(table_layout)
            splitter.addWidget(table_container)



        layout.addWidget(splitter)
        layout.addStretch(0)

        # layout.addStretch()
        widget = QtWidgets.QWidget(self)
        widget.setLayout(layout)
        return widget

    def populate(self, key):
        self.activity = bw.get_activity(key)

        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)
        self.metadata.populate(self.activity)
