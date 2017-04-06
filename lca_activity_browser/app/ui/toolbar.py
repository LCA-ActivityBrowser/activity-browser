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
    def __init__(self, window, *args):
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


class Toolbar(QtGui.QToolBar):
    def __init__(self, window):
        super(Toolbar, self).__init__()
        self.window = window

        # Toolbar elements are layed out left to right.
        new_issue_button = QtGui.QPushButton(QtGui.QIcon(icons.debug), 'Report Bug')
        new_issue_button.setStyleSheet('QPushButton {color: red;}')

        switch_stack_button = StackButton(
            self.window,
            QtGui.QIcon(icons.switch),
            'Debug window',
        )
        switch_stack_button.clicked.connect(switch_stack_button.switch_state)

        self.project_name_label = QtGui.QLabel('Project: default')
        self.project_read_only = QtGui.QLabel('Substititue me')
        self.project_read_only.setStyleSheet('QLabel {color: red;}')
        if projects.read_only:
            print("Setting RO text")
            self.project_read_only.setText('Read Only Project')

        self.new_project_button = QtGui.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtGui.QPushButton(QtGui.QIcon(icons.copy), 'Copy')
        self.delete_project_button = QtGui.QPushButton(QtGui.QIcon(icons.delete), 'Delete')
        self.projects_list_widget = ProjectListWidget()

        self.addWidget(QtGui.QLabel('Brightway2 Activity Browser'))
        self.addWidget(new_issue_button)
        self.addWidget(switch_stack_button)
        self.addWidget(self.project_name_label)
        self.addWidget(self.project_read_only)

        spacer = QtGui.QWidget()
        spacer.setSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding
        )
        self.addWidget(spacer)
        self.addSeparator()

        self.addWidget(QtGui.QLabel('Current Project:'))
        self.addWidget(self.projects_list_widget)
        self.addWidget(self.new_project_button)
        self.addWidget(self.copy_project_button)
        self.addWidget(self.delete_project_button)


        self.window.addToolBar(self)

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

        self.project_name_label.setText('Project: {}'.format(projects.current))
        self.project_read_only.setText('')
        if projects.read_only:
            self.project_read_only.setText('Read Only Project')
            self.window.warning("Read Only Project", """Read Only Project.\nAnother Python process is working with this project, no writes are allowed.\nCheck to make sure no other Python interpreters are running, and then re-select this project.""")

    # def get_search_box(self):
    #     search_box = QtGui.QLineEdit()
    #     search_box.setMaximumSize(QtCore.QSize(150, 25))

    #     # Search
    #     search_action = QtGui.QAction(
    #         QtGui.QIcon(icons.search),
    #         'Search activites (see help for search syntax)',
    #         self.window
    #     )
    #     return search_box

    # def get_key_search(self):
    #     key_search_action = QtGui.QAction(
    #         QtGui.QIcon(icons.key),
    #         'Search by key',
    #         self.window
    #     )
    #     # key_search_action.triggered.connect(self.search_by_key)
    #     return key_search_action
