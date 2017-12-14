# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .. import header
from ..icons import icons
from ..tables import (
    ActivitiesTable,
    DatabasesTable,
    BiosphereFlowsTable,
    ProjectListWidget,
)
from ...signals import signals

sizePolicy_preferred = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                   QtWidgets.QSizePolicy.Preferred)
sizePolicy_maximum = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum,
                                   QtWidgets.QSizePolicy.Maximum)

sizePolicy_minimum = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                   QtWidgets.QSizePolicy.Minimum)

sizePolicy_ignored = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                   QtWidgets.QSizePolicy.Ignored)

class NewInventoryTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(NewInventoryTab, self).__init__(parent)
        # main widgets
        self.projects_widget = ProjectsWidget()
        self.databases_widget = DatabaseWidget()
        self.activities_widget = ActivitiesWidget()
        self.flows_widget = BiosphereFlowsWidget()

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)
        # self.overall_layout.addStretch(0)
        self.overall_layout.addWidget(self.databases_widget)
        # self.overall_layout.addStretch(0)
        self.overall_layout.addWidget(self.activities_widget)
        # self.overall_layout.addStretch(100)
        self.overall_layout.addWidget(self.flows_widget)
        # self.overall_layout.addStretch(100)
        self.setLayout(self.overall_layout)

        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.black)
        self.setPalette(p)

        # self.setSizePolicy(sizePolicy)

        self.connect_signals()

    def connect_signals(self):
        signals.database_selected.connect(self.update_widgets)

    def update_widgets(self):
        if self.activities_widget.activities_table.rowCount() == 0:
            self.activities_widget.hide()
        else:
            self.activities_widget.show()
            # self.activities_widget.resize((QtWidgets.QWidget.sizeHint(self.activities_widget)))
            # self.activities_widget.resize()
            # self.activities_widget.resize()
            # self.adjustSize()
            # self.activities_widget.adjustSize()
            # self.activities_widget.activities_table.adjustSize()
            # self.activities_widget.adjustSize()
            # self.adjustSize()

            print("Size hints:",
                  self.sizeHint(),
                  self.activities_widget.sizeHint(),
                  self.activities_widget.activities_table.sizeHint())
            print("Minimum size hints:",
                  self.minimumSizeHint(),
                  self.activities_widget.minimumSizeHint(),
                  self.activities_widget.activities_table.minimumSizeHint())
            print("Maximum heights:",
                  self.maximumHeight(),
                  self.activities_widget.maximumHeight(),
                  self.activities_widget.activities_table.maximumHeight())
            # self.activities_widget.setMinimumHeight(1000)
            # self.activities_widget.activities_table.setMinimumHeight(1000)
            # self.resize(self.sizeHint())
        if self.flows_widget.flows_table.rowCount() == 0:
            self.flows_widget.hide()
        else:
            self.flows_widget.show()

class ProjectsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ProjectsWidget, self).__init__()

        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.red)
        self.setPalette(p)

        self.projects_list = ProjectListWidget()
        # Buttons
        self.new_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.copy), 'Copy current')
        self.delete_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.delete), 'Delete current')
        # Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(header('Current Project:'))
        self.h_layout.addWidget(self.projects_list)
        self.h_layout.addWidget(self.new_project_button)
        self.h_layout.addWidget(self.copy_project_button)
        self.h_layout.addWidget(self.delete_project_button)
        # self.h_layout.addStretch()
        self.setLayout(self.h_layout)
        # self.setSizePolicy(sizePolicy)


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self):
        super(DatabaseWidget, self).__init__()
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.blue)
        self.setPalette(p)
        print("HERE")
        self.databases_table = DatabasesTable()
        self.databases_table.name = "Hugo"
        print("Database table: ", id(self.databases_table), self.databases_table.name)
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        v_layout.addWidget(header('Database'))
        v_layout.addWidget(self.databases_table)
        # v_layout.addStretch()
        self.setLayout(v_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Maximum)
        )


class ActivitiesWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ActivitiesWidget, self).__init__()
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.gray)
        self.setPalette(p)


        # sizePolicy.setHeightForWidth(True)
        # self.setSizePolicy(sizePolicy_minimum)

        self.activities_table = ActivitiesTable()
        # self.activities_table.setSizePolicy(sizePolicy_minimum)
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        # v_layout.size
        v_layout.addWidget(header('Activities'))
        v_layout.addWidget(self.activities_table)
        # v_layout.addStretch(100)
        self.setLayout(v_layout)



class BiosphereFlowsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(BiosphereFlowsWidget, self).__init__()
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtCore.Qt.green)
        self.setPalette(p)
        self.flows_table = BiosphereFlowsTable()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        v_layout.addWidget(header('Biosphere Flows'))
        v_layout.addWidget(self.flows_table)
        # v_layout.addStretch()
        self.setLayout(v_layout)