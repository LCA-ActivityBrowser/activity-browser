# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..signals import signals
from .icons import icons
from .tables import ProjectListWidget
from brightway2 import projects
from PyQt4 import QtCore, QtGui, QtWebKit
from requests_oauthlib import OAuth1Session
import requests


def create_issue(content):
    issues = OAuth1Session(
        '4DBX8xKMvaUShgUHW9',
        client_secret='Lzman2V4v52YqMHazNNrpstHSLGgyhWH'
    )
    data = {
        'title': 'New issue reported from app',
        'content': content,
        'status': 'new',
        'priority': 'trivial',
        'kind': 'bug'
    }
    URL = "https://bitbucket.org/api/1.0/repositories/cmutel/activity-browser/issues/"
    issues.post(URL, data=data)


class StackButton(QtGui.QPushButton):
    def __init__(self, *args, window=None):
        super(StackButton, self).__init__(*args)
        self.state = 1
        self.window = window

    def switch_state(self):
        if self.state == 0:
            self.state = 1
            self.window.stacked.setCurrentWidget(self.window.main_widget)
            self.setText("Debug window")
        else:
            self.state = 0
            self.window.stacked.setCurrentWidget(self.window.working_widget)
            self.setText("Main window")


class Toolbar(object):
    def __init__(self, window):
        self.window = window

        # Toolbar elements are layed out left to right.
        # First is a search box, then a bunch of actions

        # self.search_box = self.get_search_box()
        # self.key_search_action = self.get_key_search()

        new_issue_button = QtGui.QPushButton(QtGui.QIcon(icons.debug), 'Report Bug')
        new_issue_button.setStyleSheet('QPushButton {color: red;}')
        # button.setText('Report Bug')

        switch_stack_button = StackButton(
            QtGui.QIcon(icons.switch),
            'Debug window',
            window=self.window
        )
        switch_stack_button.clicked.connect(switch_stack_button.switch_state)

        self.new_project_button = QtGui.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtGui.QPushButton(QtGui.QIcon(icons.copy), 'Copy')
        self.delete_project_button = QtGui.QPushButton(QtGui.QIcon(icons.delete), 'Delete')
        self.projects_list_widget = ProjectListWidget()

        self.toolbar = QtGui.QToolBar('Toolbar')
        # self.toolbar.addWidget(self.search_box)
        self.toolbar.addWidget(QtGui.QLabel('Brightway2 Activity Browser'))
        self.toolbar.addWidget(new_issue_button)
        self.toolbar.addWidget(switch_stack_button)

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
        new_issue_button.clicked.connect(self.create_issue_dialog)

    def create_issue_dialog(self):
        text = self.window.dialog(
            'Report new bug',
            'Please describe the buggy behaviour. Existing bugs can be viewed at `https://bitbucket.org/cmutel/activity-browser/issues?status=new&status=open`'
        )
        if text:
            create_issue(text)

    def connect_signals(self, controller):
        self.projects_list_widget.currentIndexChanged['QString'].connect(
            controller.select_project
        )
        self.new_project_button.clicked.connect(controller.new_project)
        self.delete_project_button.clicked.connect(controller.delete_project)
        self.copy_project_button.clicked.connect(controller.copy_project)

    def change_project(self, name):
        index = sorted([project.name for project in projects]).index(projects.current)
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
