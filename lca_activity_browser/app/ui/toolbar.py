# -*- coding: utf-8 -*-
from brightway2 import projects
from PyQt5 import QtGui, QtWidgets
from requests_oauthlib import OAuth1Session

from .icons import icons
from ..signals import signals


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


class StackButton(QtWidgets.QPushButton):
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


class Toolbar(QtWidgets.QToolBar):
    def __init__(self, window):
        super(Toolbar, self).__init__()
        self.window = window

        # Toolbar elements are layed out left to right.
        new_issue_button = QtWidgets.QPushButton(QtGui.QIcon(icons.debug), 'Report Bug')
        new_issue_button.setStyleSheet('QPushButton {color: red;}')

        switch_stack_button = StackButton(
            self.window,
            QtGui.QIcon(icons.switch),
            'Debug window',
        )
        switch_stack_button.clicked.connect(switch_stack_button.switch_state)

        self.project_name_label = QtWidgets.QLabel('Project: default')
        self.project_read_only = QtWidgets.QLabel('Read only')
        self.project_read_only.setStyleSheet('QLabel {color: red;}')
        if projects.read_only:
            print("Setting RO text")
            self.project_read_only.setText('Read Only Project')

        self.change_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.load_db), 'Change')
        self.new_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.copy), 'Copy current')
        self.delete_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.delete), 'Delete current')

        self.addWidget(QtWidgets.QLabel('Brightway2 Activity Browser'))
        self.addWidget(new_issue_button)
        self.addWidget(switch_stack_button)
        self.addWidget(self.project_name_label)
        self.addWidget(self.project_read_only)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self.addWidget(spacer)
        self.addSeparator()

        self.addWidget(QtWidgets.QLabel('Projects:'))
        self.addWidget(self.change_project_button)
        self.addWidget(self.new_project_button)
        self.addWidget(self.copy_project_button)
        self.addWidget(self.delete_project_button)

        self.window.addToolBar(self)

        new_issue_button.clicked.connect(self.create_issue_dialog)

        self.connect_signals()

    def connect_signals(self):
        self.change_project_button.clicked.connect(signals.change_project_dialogue.emit)
        self.new_project_button.clicked.connect(signals.new_project.emit)
        self.delete_project_button.clicked.connect(signals.delete_project.emit)
        self.copy_project_button.clicked.connect(signals.copy_project.emit)

        signals.project_selected.connect(self.set_project_label)

    def create_issue_dialog(self):
        text = self.window.dialog(
            'Report new bug',
            'Please describe the buggy behaviour. Existing bugs can be viewed at `https://bitbucket.org/cmutel/activity-browser/issues?status=new&status=open`'
        )
        if text:
            create_issue(text)

    def set_project_label(self):
        name = projects.current
        self.project_name_label.setText('Project: {}'.format(name))
        self.project_read_only.setText('')
        if projects.read_only:
            self.project_read_only.setText('Read Only Project')
            self.window.warning("Read Only Project", """Read Only Project.\nAnother Python process is working with this project, no writes are allowed.\nCheck to make sure no other Python interpreters are running, and then re-select this project.""")

    # def get_search_box(self):
    #     search_box = QtWidgets.QLineEdit()
    #     search_box.setMaximumSize(QtCore.QSize(150, 25))

    #     # Search
    #     search_action = QtWidgets.QAction(
    #         QtGui.QIcon(icons.search),
    #         'Search activites (see help for search syntax)',
    #         self.window
    #     )
    #     return search_box

    # def get_key_search(self):
    #     key_search_action = QtWidgets.QAction(
    #         QtGui.QIcon(icons.key),
    #         'Search by key',
    #         self.window
    #     )
    #     # key_search_action.triggered.connect(self.search_by_key)
    #     return key_search_action
