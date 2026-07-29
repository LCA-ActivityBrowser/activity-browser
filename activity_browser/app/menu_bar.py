from importlib.metadata import version
from loguru import logger

import bw2data as bd

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import QSize, QUrl, Qt

from activity_browser import app
from activity_browser.bwutils.commontasks import fetch_remote_projects, get_templates

from ..ui.icons import qicons


class MenuBar(QtWidgets.QMenuBar):
    """
    Main menu bar at the top of the Activity Browser window. Contains submenus for different user interaction categories
    """
    def __init__(self, window):
        super().__init__(parent=window)

        self.project_menu = ProjectMenu(self)
        self.database_menu = DatabaseMenu(self)
        self.impact_categories_menu = ImpactCategoriesMenu(self)
        self.calculate_menu = CalculateMenu(self)
        self.view_menu = ViewMenu(self)
        self.help_menu = HelpMenu(self)

        self.addMenu(self.project_menu)
        self.addMenu(self.database_menu)
        self.addMenu(self.impact_categories_menu)
        self.addMenu(self.calculate_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.help_menu)

        self.search_button = QtWidgets.QPushButton(self)
        self.search_button.setFlat(True)
        self.search_button.setIcon(qicons.search)
        self.search_button.setIconSize(QtCore.QSize(13, 13))
        self.search_button.setToolTip("Search project (Ctrl+Shift+F)")
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.clicked.connect(app.actions.NodeSelectOpen.run)
        self.setCornerWidget(self.search_button, Qt.Corner.TopRightCorner)


class ProjectMenu(QtWidgets.QMenu):
    """Project lifecycle: open, create, duplicate, export, delete, and manage projects."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("&Project")

        self.dup_proj_action = app.actions.ProjectDuplicate.get_QAction(parent=self)
        self.export_proj_action = app.actions.ProjectExport.get_QAction(parent=self)
        self.delete_proj_action = app.actions.ProjectDelete.get_QAction(parent=self)
        self.manage_proj_action = app.actions.ProjectManagerOpen.get_QAction(parent=self)

        self.open_menu = ProjectSelectionMenu(self)
        self.new_menu = ProjectNewMenu(self)

        self.addMenu(self.open_menu)
        self.addMenu(self.new_menu)
        self.addAction(self.dup_proj_action)
        self.addAction(self.export_proj_action)
        self.addAction(self.delete_proj_action)
        self.addSeparator()
        self.addAction(self.manage_proj_action)


class DatabaseMenu(QtWidgets.QMenu):
    """Database create, import, and export."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("&Database")

        # Keep Python refs: QActions created with parent=None are otherwise GC'd
        # and vanish from the menu (PySide).
        self.new_db_action = app.actions.DatabaseNew.get_QAction(parent=self)
        self.import_menu = ImportDatabaseMenu(self)
        self.export_menu = ExportDatabaseMenu(self)

        self.addAction(self.new_db_action)
        self.addSeparator()
        self.addMenu(self.import_menu)
        self.addMenu(self.export_menu)


class ImpactCategoriesMenu(QtWidgets.QMenu):
    """Impact category (LCIA method) import."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("&Impact categories")

        self.import_menu = ImportICMenu(self)
        self.addMenu(self.import_menu)


class ProjectNewMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("New")
        self.new_proj_action = app.actions.ProjectNew.get_QAction(parent=self)
        self.import_proj_action = app.actions.ProjectImport.get_QAction(parent=self)
        self.template_menu = ProjectNewTemplateMenu(self)

        self.addAction(self.new_proj_action)
        self.addAction(self.import_proj_action)
        self.addMenu(self.template_menu)


class ProjectNewTemplateMenu(QtWidgets.QMenu):
    remote_projects = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Import from template")

        self.actions = {}

        for key in get_templates():
            action = app.actions.ProjectNewFromTemplate.get_QAction(key, parent=self)
            action.setText(key)
            self.actions[key] = action
            self.addAction(action)

        for key in self.get_projects():
            action = app.actions.ProjectNewRemote.get_QAction(key, parent=self)
            action.setText(key)
            self.actions[key] = action
            self.addAction(action)

    def get_projects(self):
        if not self.remote_projects:
            ProjectNewTemplateMenu.remote_projects = fetch_remote_projects()
        return self.remote_projects


class ViewMenu(QtWidgets.QMenu):
    """
    View menu: contains actions in regard to hiding and showing specific UI elements.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("&View")


class CalculateMenu(QtWidgets.QMenu):
    """
    Calculate Menu: contains actions in regard to calculating the LCA results for the current project
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("&Calculate")
        self.cs_actions = []

        self.new_cs_action = app.actions.CSNew.get_QAction(parent=self)
        self.addAction(self.new_cs_action)
        self.addSeparator()

        app.signals.project.changed.connect(self.sync)
        app.signals.meta.calculation_setups_changed.connect(self.sync)

    def sync(self):
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        for action in self.cs_actions:
            self.removeAction(action)
        self.cs_actions.clear()
        for cs in bd.calculation_setups:
            action = app.actions.CSOpen.get_QAction(cs, parent=self)
            action.setText(cs)
            self.cs_actions.append(action)
            self.addAction(action)


class HelpMenu(QtWidgets.QMenu):
    """
    Help Menu: contains actions that show info to the user or redirect them to online resources
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("&Help")

        self.addAction(
            qicons.ab, "&About Activity Browser", self.about
        )
        self.addAction(
            "&About Qt", lambda: QtWidgets.QMessageBox.aboutQt(app.main_window)
        )
        self.addAction(
            qicons.question, "&Get help on the wiki", self.open_wiki
        )
        self.addAction(
            qicons.issue, "&Report an idea/issue on GitHub", self.raise_issue_github
        )

    def about(self):
        """Displays an 'about' window to the user containing e.g. the version of the AB and copyright info"""
        text = f"""
        Activity Browser - a graphical interface for Brightway2.<br><br>
        Application version: <b>{version("activity_browser")}</b><br>
        bw2data version: <b>{version("bw2data")}</b><br>
        bw2io version: <b>{version("bw2io")}</b><br>
        bw2calc version: <b>{version("bw2calc")}</b><br><br>
        All development happens on <a href="https://github.com/LCA-ActivityBrowser/activity-browser">github</a>.<br><br>
        For copyright information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/tree/main#copyright">this page</a>.<br><br>
        For license information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt">this page</a>.<br><br>
        """

        about_window = QtWidgets.QMessageBox(parent=app.main_window)
        about_window.setWindowTitle("About the Activity Browser")
        about_window.setIconPixmap(qicons.ab.pixmap(QSize(150, 150)))
        about_window.setText(text)

        about_window.exec_()

    def open_wiki(self):
        """Opens the AB github wiki in the users default browser"""
        url = QUrl(
            "https://github.com/LCA-ActivityBrowser/activity-browser/wiki"
        )
        QtGui.QDesktopServices.openUrl(url)

    def raise_issue_github(self):
        """Opens the github create issue page in the users default browser"""
        url = QUrl(
            "https://github.com/LCA-ActivityBrowser/activity-browser/issues/new/choose"
        )
        QtGui.QDesktopServices.openUrl(url)


class ProjectSelectionMenu(QtWidgets.QMenu):
    """
    Menu that lists all the projects available through bw2data.projects
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Open")
        self.populate()

        self.aboutToShow.connect(self.populate)
        self.triggered.connect(lambda act: app.actions.ProjectSwitch.run(act.data()))

    def populate(self):
        """
        Populates the menu with the projects available in the database
        """
        import bw2data as bd

        # clear the menu of any already existing actions
        self.clear()

        # sort projects alphabetically
        sorted_projects = sorted(list(bd.projects))

        # iterate over the sorted projects and add them as actions to the menu
        for i, proj in enumerate(sorted_projects):
            # check whether the project is BW25
            bw_25 = (
                False if not isinstance(proj.data, dict) else proj.data.get("25", False)
            )

            # create the action and disable it if it's BW25 and BW25 is not supported
            action = QtWidgets.QAction(proj.name, self)
            action.setData(proj.name)
            action.setIcon(
                app.application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning) if not bw_25 else qicons.empty)

            self.addAction(action)


class ImportDatabaseMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Import")
        self.setIcon(qicons.import_db)

        self.import_from_excel_action = app.actions.DatabaseImporterExcel.get_QAction(parent=self)
        self.import_from_bw2package_action = app.actions.DatabaseImporterBW2Package.get_QAction(parent=self)
        self.import_from_ecoinvent_action = app.actions.DatabaseImportFromEcoinvent.get_QAction(parent=self)

        self.addAction(self.import_from_excel_action)
        self.addAction(self.import_from_bw2package_action)
        self.addSeparator()
        self.addAction(self.import_from_ecoinvent_action)


class ExportDatabaseMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Export")

        self.export_to_excel_action = app.actions.DatabaseExportExcel.get_QAction(parent=self)
        self.export_to_bw2package_action = app.actions.DatabaseExportBW2Package.get_QAction(parent=self)

        self.addAction(self.export_to_excel_action)
        self.addAction(self.export_to_bw2package_action)


class ImportICMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Import")
        self.setIcon(qicons.import_db)

        self.import_from_ei_excel_action = app.actions.MethodImporterEcoinvent.get_QAction(parent=self)
        self.import_from_bw2io_action = app.actions.MethodImporterBW2IO.get_QAction(parent=self)

        self.addAction(self.import_from_ei_excel_action)
        self.addAction(self.import_from_bw2io_action)
