from logging import getLogger

import pandas as pd
from qtpy import QtWidgets, QtCore

import bw2data as bd
from bw2io import remote

from activity_browser import actions, ui, signals, utils
from activity_browser.settings import ab_settings
from activity_browser.ui import widgets


log = getLogger(__name__)


class ProjectManagerPane(widgets.ABAbstractPane):
    title = "Project Manager"
    unique = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Manager")

        self.tabs = QtWidgets.QTabWidget(self)

        self.project_model = widgets.ABItemModel(self)
        self.project_model.dataItemClass = ProjectItem

        self.template_model = widgets.ABItemModel(self)
        self.template_model.dataItemClass = TemplateItem

        self.project_view = ProjectView(self)
        self.project_view.setModel(self.project_model)

        self.template_view = TemplateView(self)
        self.template_view.setModel(self.template_model)

        self.sync()

        self.tabs.addTab(self.project_view, "Projects")
        self.tabs.addTab(self.template_view, "Templates")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # connect signals
        signals.project.changed.connect(self.sync)
        signals.project.deleted.connect(self.sync)

    def sync(self):
        self.project_model.setDataFrame(self.build_project_df())
        self.template_model.setDataFrame(self.build_template_df())

    def build_project_df(self) -> pd.DataFrame:
        data = {}
        for proj_ds in sorted(bd.projects):
            # if for any reason the project data is not a dictionary, log a warning and set it to an empty dict
            if not isinstance(proj_ds.data, dict):
                log.warning(f"Project {proj_ds.name} has no data dictionary")
                proj_ds.data = {}

            data[proj_ds.name] = {
                "Name": proj_ds.name,
                "Path": proj_ds.dir,
                "Version": "Brightway25" if proj_ds.data.get("25", False) else "Legacy"
            }

        return pd.DataFrame.from_dict(data, orient="index")

    def build_template_df(self) -> pd.DataFrame:
        data = {}

        templates = utils.get_templates()
        remote_templates = remote.get_projects()

        for name in sorted(templates):
            data[name] = {
                "Name": name,
                "Path": templates[name],
                "Remote": "No"
            }

        for name in sorted(remote_templates):
            data[name] = {
                "Name": name,
                "Path": remote_templates[name],
                "Remote": "Yes"
            }

        return pd.DataFrame.from_dict(data, orient="index")


class ProjectView(widgets.ABTreeView):

    class ContextMenu(widgets.ABTreeView.ContextMenu):
        def __init__(self, pos, view: "FunctionView"):
            from activity_browser.ui.menu_bar import ProjectNewMenu

            super().__init__(pos, view)
            items = list({index.internalPointer() for index in view.selectedIndexes()})

            self.addMenu(ProjectNewMenu(self))

            if len(items) == 0:
                return

            if len(items) == 1:
                self.dup_project = actions.ProjectDuplicate.get_QAction(items[0]["Name"])
                self.template_project = actions.ProjectCreateTemplate.get_QAction(items[0]["Name"], view.parent())
                self.addAction(self.dup_project)
                self.addAction(self.template_project)

            if len(items) == 1 and len([i for i in items if i["Version"] == "Legacy"]) == 1:
                self.migrate_project = actions.ProjectMigrate25.get_QAction(items[0]["Name"])
                self.addAction(self.migrate_project)

            self.del_project = actions.ProjectDelete.get_QAction(view.selected_projects)
            self.addAction(self.del_project)


    def __init__(self, parent: ProjectManagerPane):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)


    @property
    def selected_projects(self) -> [str]:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProjectItem)]
        return list({item["Name"] for item in items if item["Name"] is not None})


class ProjectItem(widgets.ABDataItem):
    def decorationData(self, col, key):
        if col != 0:
            return
        return ui.icons.qicons.forward if self["Name"] == ab_settings.startup_project else ui.icons.QIcons.forward


class TemplateView(widgets.ABTreeView):

    class ContextMenu(widgets.ABTreeView.ContextMenu):
        def __init__(self, pos, view: "FunctionView"):
            super().__init__(pos, view)

            items = list({index.internalPointer() for index in view.selectedIndexes()})

    def __init__(self, parent: ProjectManagerPane):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)


class TemplateItem(widgets.ABDataItem):
    def decorationData(self, col, key):
        if col != 0:
            return
        return ui.icons.qicons.forward if self["Name"] == ab_settings.startup_project else ui.icons.QIcons.forward
