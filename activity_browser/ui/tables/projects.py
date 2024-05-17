# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QComboBox, QSizePolicy
from PySide2.QtCore import Qt

from activity_browser.brightway import bd


class ProjectListWidget(QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = []

        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Maximum)
        )

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        bd.projects.list_changed.connect(self.sync)
        bd.projects.current_changed.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names.clear()

        for i, proj in enumerate(bd.projects):
            bw_25 = False if not isinstance(proj.data, dict) else proj.data.get("25", False)
            name = proj.name if not bw_25 else "[BW25] " + proj.name

            self.addItem(name)
            self.project_names.append(name)
            self.setItemData(i, name, Qt.ToolTipRole)
            self.model().item(i).setEnabled(not bw_25)

        index = self.project_names.index(bd.projects.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        # TODO: create an action for this
        bd.projects.set_current(self.project_names[index])