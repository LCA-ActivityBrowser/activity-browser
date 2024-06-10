import os

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QComboBox, QSizePolicy

from activity_browser import actions
from activity_browser.mod import bw2data as bd

AB_BW25 = True if os.environ.get("AB_BW25", False) else False


class ProjectListWidget(QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = []

        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        bd.projects.list_changed.connect(self.sync)
        bd.projects.current_changed.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names.clear()

        sorted_projects = sorted(list(bd.projects))

        for i, proj in enumerate(sorted_projects):
            bw_25 = (
                False if not isinstance(proj.data, dict) else proj.data.get("25", False)
            )
            name = proj.name if not bw_25 or AB_BW25 else "[BW25] " + proj.name

            self.addItem(name)
            self.project_names.append(name)
            self.setItemData(i, name, Qt.ToolTipRole)
            self.model().item(i).setEnabled(not bw_25 or AB_BW25)

        index = self.project_names.index(bd.projects.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        actions.ProjectSwitch.run(self.project_names[index])
