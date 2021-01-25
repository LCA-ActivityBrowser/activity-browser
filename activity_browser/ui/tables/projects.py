# -*- coding: utf-8 -*-
from bw2data import projects
from PySide2.QtWidgets import QComboBox

from ...signals import signals


class ProjectListWidget(QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = None

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        signals.project_selected.connect(self.sync)
        signals.projects_changed.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names = sorted([project.name for project in projects])
        self.addItems(self.project_names)
        index = self.project_names.index(projects.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        signals.change_project.emit(self.project_names[index])
