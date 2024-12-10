import os

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QSizePolicy

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
        alternative_default = None

        for i, proj in enumerate(sorted_projects):
            bw_25 = (
                False if not isinstance(proj.data, dict) else proj.data.get("25", False)
            )
            if bw_25 and alternative_default is None:
                alternative_default = proj.name
            name = proj.name if bw_25 else "[BW2] " + proj.name

            self.addItem(name)
            self.project_names.append(name)
            self.setItemData(i, name, Qt.ToolTipRole)
            self.model().item(i).setEnabled(not bw_25 or AB_BW25)

        try:
            index = self.project_names.index(bd.projects.current)
        except ValueError:
            # Current project not in given project names!?
            # Sync error between AB settings and Brightway project management
            if alternative_default is not None:
                index = self.project_names.index(alternative_default)
                bd.projects.set_current(alternative_default)
            else:
                # Create new project
                bd.projects.set_current("default-bw25")
                index = self.project_names.index("default-bw25")
        self.setCurrentIndex(index)

    def on_activated(self, index):
        actions.ProjectSwitch.run(self.project_names[index])
