# -*- coding: utf-8 -*-
from loguru import logger

import pandas as pd
from qtpy import QtWidgets, QtGui

import bw2data as bd
from bw2io import remote

from activity_browser import app, ui
from activity_browser.bwutils.commontasks import get_templates
from activity_browser.ui import widgets, core

from .base import BaseSettingsChapter


class ProjectManagerSettingsChapter(BaseSettingsChapter):
    """Chapter for project and template management."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tabs = QtWidgets.QTabWidget(self)

        self.project_model = ProjectModel(parent=self)
        self.template_model = TemplateModel(parent=self)

        self.project_view = ProjectView(self)
        self.project_view.setModel(self.project_model)

        self.template_view = TemplateView(self)
        self.template_view.setModel(self.template_model)

        self.tabs.addTab(self.project_view, "Projects")
        self.tabs.addTab(self.template_view, "Templates")

        self.build_layout()
        self.connect_signals()
        self.reset()

    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def connect_signals(self):
        """Connect signals and slots."""
        app.signals.project.changed.connect(self.sync)
        app.signals.project.deleted.connect(self.sync)

    def sync(self):
        """Sync project and template data."""
        df = self.build_project_df()
        self.project_model.set_dataframe(df)
        self.project_view.resizeColumnToContents(1)
        
        df = self.build_template_df()
        self.template_model.set_dataframe(df)
        self.template_view.resizeColumnToContents(1)

    def reset(self):
        """Reset to initial values."""
        self.sync()

    def has_changes(self):
        """Project manager doesn't have editable settings."""
        return False

    def set_settings(self):
        """No settings to save for project manager."""
        pass

    def build_project_df(self) -> pd.DataFrame:
        """Build DataFrame for projects."""
        data = []
        for proj_ds in sorted(bd.projects):
            # if for any reason the project data is not a dictionary, log a warning and set it to an empty dict
            if not isinstance(proj_ds.data, dict):
                logger.warning(f"Project {proj_ds.name} has no data dictionary")
                proj_ds.data = {}

            data.append({
                "name": proj_ds.name,
                "path": proj_ds.dir,
                "version": "Brightway25" if proj_ds.data.get("25", False) else "Legacy"
            })

        cols = ["name", "version", "path"]
        return pd.DataFrame(data, columns=cols)

    def build_template_df(self) -> pd.DataFrame:
        """Build DataFrame for templates."""
        data = []

        templates = get_templates()
        remote_templates = remote.get_projects()

        for name in sorted(templates):
            data.append({
                "name": name,
                "path": templates[name],
                "remote": "No"
            })

        for name in sorted(remote_templates):
            data.append({
                "name": name,
                "path": remote_templates[name],
                "remote": "Yes"
            })

        cols = ["name", "path", "remote"]
        return pd.DataFrame(data, columns=cols)


class ProjectView(widgets.ABTreeView):

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.addMenu(p.get_project_new_menu(m)),
            lambda m, p: m.addSeparator() if p.has_selection else None,
            lambda m, p: m.add(app.actions.ProjectDuplicate, p.selected_project,
                              enable=p.single_selection) if p.single_selection else None,
            lambda m, p: m.add(app.actions.ProjectCreateTemplate, p.selected_project, m.parent(),
                              enable=p.single_selection) if p.single_selection else None,
            lambda m, p: m.add(app.actions.ProjectMigrate25, p.selected_project,
                              enable=(p.single_selection and p.is_legacy)) if p.single_selection and p.is_legacy else None,
            lambda m, p: m.addSeparator() if p.has_selection else None,
            lambda m, p: m.add(app.actions.ProjectDelete, p.selected_projects,
                              enable=p.has_selection) if p.has_selection else None,
        ]

    def __init__(self, parent):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    
    def get_project_new_menu(self, parent):
        """Get the ProjectNewMenu."""
        from activity_browser.app.menu_bar import ProjectNewMenu
        return ProjectNewMenu(parent)

    @property
    def selected_projects(self) -> list:
        if not self.selectedIndexes():
            return []
        names = self.model().values_from_indices("name", self.selectedIndexes())
        return list(set(names))
    
    @property
    def selected_project(self):
        return self.selected_projects[0] if self.single_selection else None
    
    @property
    def single_selection(self):
        return len(self.selected_projects) == 1
    
    @property
    def has_selection(self):
        return len(self.selected_projects) > 0
    
    @property
    def is_legacy(self):
        if not self.single_selection:
            return False
        index = self.selectedIndexes()[0]
        return self.model().get(index, "version") == "Legacy"


class ProjectModel(core.ABTreeModel):
    """Model for project data."""
    
    def fontData(self, index):
        """Provide font data for the model."""
        column_name = self.column_name(index)
        
        if column_name == "name":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font
        
        return None
    
    def decorationData(self, index):
        """Provide icon decoration for the model."""
        column_name = self.column_name(index)
        
        if column_name == "name":
            name = self.get(index, "name")
            if name == app.settings["startup"]["startup_project"]:
                return ui.icons.qicons.star
            if name == bd.projects.current:
                return ui.icons.qicons.forward

            return ui.icons.qicons.empty
        
        return None


class TemplateView(widgets.ABTreeView):

    class ContextMenu(widgets.ABMenu):
        menuSetup = []

    def __init__(self, parent):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)


class TemplateModel(core.ABTreeModel):
    """Model for template data."""
    
    def fontData(self, index):
        """Provide font data for the model."""
        column_name = self.column_name(index)
        
        if column_name == "name":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font
        
        return None
    

