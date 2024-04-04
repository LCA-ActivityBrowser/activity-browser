# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QComboBox
from PySide2.QtCore import Qt

from activity_browser import signals, project_controller


class ProjectListWidget(QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = None

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        project_controller.projects_changed.connect(self.sync)
        project_controller.project_switched.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names = sorted([project.name for project in project_controller])
        self.addItems(self.project_names)
        for i, name in enumerate(self.project_names):
            self.setItemData(i, name, Qt.ToolTipRole)
        index = self.project_names.index(project_controller.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        project_controller.set_current(self.project_names[index])
