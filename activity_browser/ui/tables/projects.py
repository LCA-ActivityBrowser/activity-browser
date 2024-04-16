# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QComboBox
from PySide2.QtCore import Qt

from activity_browser.brightway.bw2data import projects


class ProjectListWidget(QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = None

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        projects.list_changed.connect(self.sync)
        projects.current_changed.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names = sorted([project.name for project in projects])
        self.addItems(self.project_names)
        for i, name in enumerate(self.project_names):
            self.setItemData(i, name, Qt.ToolTipRole)
        index = self.project_names.index(projects.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        # TODO: create an action for this
        projects.set_current(self.project_names[index])