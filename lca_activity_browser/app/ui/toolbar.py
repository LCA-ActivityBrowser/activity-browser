# -*- coding: utf-8 -*-
import json
import requests
from ..signals import signals
from .icons import icons
from brightway2 import projects
from PyQt5 import QtGui, QtWidgets


def create_issue(content):
    abtoken = '01533fb30748a02f107ba1fc55a8ac2fb77b5ade'
    auth = ('ActivityBrowser', abtoken)
    data = {
        'title': 'New issue reported from app',
        'body': content,
    }
    url = 'https://api.github.com/repos/LCA-ActivityBrowser/activity-browser/issues'
    response = requests.post(url, data=json.dumps(data), auth=auth)
    if response.status_code != 201:
        print(response)
        print(response.text)


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
        # new_issue_button.setStyleSheet('QPushButton {color: red;}')

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

    def create_issue_dialog(self):
        text = self.window.dialog(
            'Report new bug',
            ('Please describe the buggy behaviour. View existing issues on ' +
             '<a href="https://github.com/LCA-ActivityBrowser/activity-browser/issues">github</a>.')
        )
        if text:
            content = text + '\n\nLog Output:\n```{}```'.format(self.window.log.toPlainText())
            create_issue(content)

    def connect_signals(self, controller):
        self.change_project_button.clicked.connect(controller.change_project)
        self.new_project_button.clicked.connect(controller.new_project)
        self.delete_project_button.clicked.connect(controller.delete_project)
        self.copy_project_button.clicked.connect(controller.copy_project)

        signals.project_selected.connect(self.set_project_label)

    def set_project_label(self, name):
        self.project_name_label.setText('Project: {}'.format(name))
        self.project_read_only.setText('')
        if projects.read_only:
            self.project_read_only.setText('Read Only Project')
            self.window.warning("Read Only Project", """Read Only Project.\nAnother Python process is working with this project, no writes are allowed.\nCheck to make sure no other Python interpreters are running, and then re-select this project.""")
