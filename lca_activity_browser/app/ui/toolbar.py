# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..signals import signals
from .icons import icons
from .tables import ProjectListWidget
from brightway2 import projects
from PyQt4 import QtCore, QtGui, QtWebKit


class Toolbar(object):
    def __init__(self, window):
        self.window = window

        # Toolbar elements are layed out left to right.
        # First is a search box, then a bunch of actions

        # self.search_box = self.get_search_box()
        # self.key_search_action = self.get_key_search()

        self.new_project_button = QtGui.QPushButton('New')
        self.copy_project_button = QtGui.QPushButton('Copy')
        self.delete_project_button = QtGui.QPushButton('Delete')
        self.projects_list_widget = ProjectListWidget()

        self.toolbar = QtGui.QToolBar('Toolbar')
        # self.toolbar.addWidget(self.search_box)
        self.toolbar.addWidget(QtGui.QLabel('Brightway2 Activity Browser'))

        spacer = QtGui.QWidget()
        spacer.setSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding
        )
        self.toolbar.addWidget(spacer)
        self.toolbar.addSeparator()

        # ACTIONS = [
        #     self.key_search_action,
        # ]
        # for action in ACTIONS:
        #     self.toolbar.addAction(action)

        # self.toolbar.addAction(action_key)
        # self.toolbar.addAction(action_random_activity)
        # self.toolbar.addAction(action_history)
        # self.toolbar.addAction(action_backward)
        # self.toolbar.addAction(action_forward)
        # self.toolbar.addAction(action_edit)
        # self.toolbar.addAction(action_calculate)

        self.toolbar.addWidget(QtGui.QLabel('Current Project:'))
        self.toolbar.addWidget(self.projects_list_widget)
        self.toolbar.addWidget(self.new_project_button)
        self.toolbar.addWidget(self.copy_project_button)
        self.toolbar.addWidget(self.delete_project_button)


        self.window.addToolBar(self.toolbar)

        signals.project_selected.connect(self.change_project)

    def connect_signals(self, controller):
        self.projects_list_widget.currentIndexChanged['QString'].connect(
            controller.select_project
        )
        self.new_project_button.clicked.connect(controller.new_project)
        self.delete_project_button.clicked.connect(controller.delete_project)

    def change_project(self, name):
        index = sorted([project.name for project in projects]).index(projects.project)
        self.projects_list_widget.setCurrentIndex(index)

    def get_search_box(self):
        search_box = QtGui.QLineEdit()
        search_box.setMaximumSize(QtCore.QSize(150, 25))

        # Search
        search_action = QtGui.QAction(
            QtGui.QIcon(icons.search),
            'Search activites (see help for search syntax)',
            self.window
        )
        # search_action.triggered.connect(self.search_results)
        # search_box.returnPressed.connect(self.search_results)

        return search_box

    def get_key_search(self):
        key_search_action = QtGui.QAction(
            QtGui.QIcon(icons.key),
            'Search by key',
            self.window
        )
        # key_search_action.triggered.connect(self.search_by_key)
        return key_search_action


        # # Random activity
        # action_random_activity = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/random_activity.png')), 'Load a random activity', self)
        # action_random_activity.triggered.connect(lambda: self.load_new_current_activity())

        # # History
        # action_history = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/history.png')), 'Previously visited activities', self)
        # action_history.triggered.connect(self.showHistory)

        # # Backward
        # action_backward = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/backward.png')), 'Go backward', self)
        # action_backward.setShortcut('Alt+left')
        # action_backward.triggered.connect(self.goBackward)

        # # Forward
        # action_forward = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/forward.png')), 'Go forward', self)
        # action_forward.setShortcut('Alt+right')
        # action_forward.triggered.connect(self.goForward)

        # # Edit
        # action_edit = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/edit.png')), 'Edit activity', self)
        # action_edit.triggered.connect(self.edit_activity)

        # # Calculate
        # action_calculate = QtGui.QAction(QtGui.QIcon(translate_icon_path('icons/calculate.png')),
        #                                'Calculate LCA (with settings in LCIA tab)', self)
        # action_calculate.triggered.connect(self.calculate_lcia)
