# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ...signals import signals
from ..graphics import DefaultGraph
from ..tables import ExchangeTableWidget
from ..widgets import ActivityDataGrid
from brightway2 import *
from PyQt4 import QtCore, QtGui
import functools


class ActivityDetailsTab(QtGui.QWidget):
    def __init__(self, parent=None, activity=None):
        super(ActivityDetailsTab, self).__init__(parent)
        self.parent = parent

        self.details_widget = self.get_details_widget()

        container = QtGui.QVBoxLayout()
        container.setAlignment(QtCore.Qt.AlignTop)
        container.addWidget(self.details_widget)

        self.setLayout(container)

        if activity:
            self.key = activity
            self.populate(activity)

    def toggle_visible(self, table):
        if table.state == "shown":
            table.state = "hidden"
            table.toggle_button.setText("hide")
            table.hide()
        else:
            table.state = "shown"
            table.show()
            table.toggle_button.setText("show")

    def get_details_widget(self):
        self.production = ExchangeTableWidget(self, production=True)
        self.inputs = ExchangeTableWidget(self)
        self.flows = ExchangeTableWidget(self, biosphere=True)
        self.upstream = ExchangeTableWidget(self)

        self.production.state = "shown"
        self.inputs.state = "shown"
        self.flows.state = "shown"
        self.upstream.state = "shown"

        layout = QtGui.QVBoxLayout()
        self.metadata = ActivityDataGrid()
        layout.addWidget(self.metadata)

        tables = [
            (self.production, "Products:"),
            (self.inputs, "Technosphere Inputs:"),
            (self.flows, "Biosphere flows:"),
            (self.upstream, "Upstream consumers:"),
        ]

        for table, label in tables:
            table.state = "shown"
            table.toggle_button = QtGui.QPushButton("Hide")
            table.toggle_button.clicked.connect(functools.partial(self.toggle_visible, table=table))

            inside_widget = QtGui.QWidget()
            inside_layout = QtGui.QHBoxLayout()
            inside_layout.addWidget(header(label))
            inside_layout.addWidget(table.toggle_button)
            inside_layout.addStretch(1)
            inside_widget.setLayout(inside_layout)

            layout.addWidget(inside_widget)
            layout.addWidget(table)

        widget = QtGui.QWidget(self)
        widget.setLayout(layout)
        return widget

    def populate(self, key):
        self.activity = get_activity(key)

        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)
        self.metadata.populate(self.activity)
