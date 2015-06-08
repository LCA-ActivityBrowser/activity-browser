# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ...signals import signals
from ..graphics import DefaultGraph
from ..tables import ExchangeTableWidget
from brightway2 import *
from PyQt4 import QtCore, QtGui
import functools


class ActivityDetailsTab(QtGui.QWidget):
    def __init__(self, parent):
        super(ActivityDetailsTab, self).__init__(parent)
        self.window = parent

        # no_activity_label = QtGui.QLabel('No activity selected yet')
        # self.no_consumption_label = QtGui.QLabel("No activities consume the reference product of this activity.")
        # self.no_consumption_label.hide()

        chart = DefaultGraph(self)
        self.details_widget = self.get_details_widget()

        placemat_layout = QtGui.QVBoxLayout()
        # placemat_layout.addWidget(no_activity_label)
        placemat_layout.addWidget(chart)

        self.placemat = QtGui.QWidget(self)
        self.placemat.setLayout(placemat_layout)

        container = QtGui.QVBoxLayout()
        container.setAlignment(QtCore.Qt.AlignTop)
        container.addWidget(self.placemat)
        container.addWidget(self.details_widget)

        self.setLayout(container)

        self.products_table_state = "shown"

        signals.project_selected.connect(lambda x: self.window.select_tab(self))
        signals.project_selected.connect(self.toggle_hidden)
        signals.activity_selected.connect(self.populate)

    def toggle_products_table(self):
        if self.products_table_state == "shown":
            self.products_table_state = "hidden"
            self.products_button.setText("hide")
            self.production.hide()
        else:
            self.products_table_state = "shown"
            self.production.show()
            self.products_button.setText("show")

    def get_details_widget(self):
        self.production = ExchangeTableWidget(self, production=True)
        self.inputs = ExchangeTableWidget(self)
        self.flows = ExchangeTableWidget(self, biosphere=True)
        self.upstream = ExchangeTableWidget(self)

        layout = QtGui.QVBoxLayout()

        self.products_button = QtGui.QPushButton("Hide")
        self.products_button.clicked.connect(self.toggle_products_table)

        inside_widget = QtGui.QWidget()
        inside_layout = QtGui.QHBoxLayout()
        inside_layout.addWidget(header('Products:'))
        inside_layout.addWidget(self.products_button)
        inside_widget.setLayout(inside_layout)

        layout.addWidget(inside_widget)
        layout.addWidget(horizontal_line())
        layout.addWidget(self.production)

        layout.addWidget(header('Inputs:'))
        layout.addWidget(horizontal_line())
        layout.addWidget(self.inputs)

        layout.addWidget(header('Biosphere flows:'))
        layout.addWidget(horizontal_line())
        layout.addWidget(self.flows)

        layout.addWidget(header('Upstream:'))
        layout.addWidget(horizontal_line())
        layout.addWidget(self.upstream)

        widget = QtGui.QWidget(self)
        widget.setLayout(layout)
        return widget

    def populate(self, key):
        activity = get_activity(key)

        self.production.set_queryset(activity.production())
        self.inputs.set_queryset(activity.technosphere())
        self.flows.set_queryset(activity.biosphere())
        self.upstream.set_queryset(activity.upstream(), upstream=True)

        self.placemat.hide()
        self.details_widget.show()

    def toggle_hidden(self):
        self.placemat.show()
        self.details_widget.hide()
