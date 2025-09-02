from importlib.metadata import version

import bw2data as bd

from qtpy import QtGui, QtWidgets
from qtpy.QtCore import QSize, QUrl

from activity_browser import actions, signals, utils, application

from .icons import qicons


class MenuBar(QtWidgets.QMenuBar):
    """
    Main menu bar at the top of the Activity Browser window. Contains submenus for different user interaction categories
    """
    def __init__(self, window):
        super().__init__(parent=window)

        self.project_menu = ProjectMenu(self)
        self.view_menu = ViewMenu(self)
        self.calculate_menu = CalculateMenu(self)
        # self.tools_menu = ToolsMenu(self)
        self.help_menu = HelpMenu(self)

        self.addMenu(self.project_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.calculate_menu)
        # self.addMenu(self.tools_menu)
        self.addMenu(self.help_menu)


class ProjectMenu(QtWidgets.QMenu):
    """
    Project menu: contains actions related to managing the project, such as project duplication, database importing etc.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("&Project")

        self.dup_proj_action = actions.ProjectDuplicate.get_QAction()
        self.delete_proj_action = actions.ProjectDelete.get_QAction()

        self.import_proj_action = actions.ProjectImport.get_QAction()
        self.export_proj_action = actions.ProjectExport.get_QAction()

        self.export_db_action = actions.DatabaseExport.get_QAction()

        self.manage_settings_action = actions.SettingsWizardOpen.get_QAction()
        self.manage_projects_action = actions.ProjectManagerOpen.get_QAction()

        self.addMenu(ProjectSelectionMenu(self))
        self.addMenu(ProjectNewMenu(self))
        self.addAction(self.dup_proj_action)
        self.addAction(self.delete_proj_action)
        self.addSeparator()
        self.addAction(self.import_proj_action)
        self.addAction(self.export_proj_action)
        self.addSeparator()
        self.addMenu(ImportDatabaseMenu(self))
        self.addAction(self.export_db_action)
        self.addSeparator()
        self.addMenu(ImportICMenu(self))
        self.addSeparator()
        self.addAction(self.manage_settings_action)
        self.addAction(self.manage_projects_action)


class ProjectNewMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle("New project")
        self.new_proj_action = actions.ProjectNew.get_QAction()
        self.import_proj_action = actions.ProjectImport.get_QAction()

        self.new_proj_action.setText("Empty project")
        self.import_proj_action.setText("From .tar.gz file")

        self.new_proj_action.setIcon(QtGui.QIcon())
        self.import_proj_action.setIcon(QtGui.QIcon())

        self.addAction(self.new_proj_action)
        self.addAction(self.import_proj_action)
        self.addMenu(ProjectNewTemplateMenu(self))


class ProjectNewTemplateMenu(QtWidgets.QMenu):
    remote_projects = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("From template")

        self.actions = {}

        for key in utils.get_templates():
            action = actions.ProjectNewFromTemplate.get_QAction(key)
            action.setText(key)
            self.actions[key] = action
            self.addAction(action)

        for key in self.get_projects():
            action = actions.ProjectNewRemote.get_QAction(key)
            action.setText(key)
            self.actions[key] = action
            self.addAction(action)

    def get_projects(self):
        if not self.remote_projects:
            from bw2io.remote import get_projects
            ProjectNewTemplateMenu.remote_projects = get_projects()
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

        self.new_cs_action = actions.CSNew.get_QAction()
        self.new_cs_action.setText("New setup...")
        self.addAction(self.new_cs_action)
        self.addSeparator()

        signals.project.changed.connect(self.sync)
        signals.meta.calculation_setups_changed.connect(self.sync)

    def sync(self):
        self.cs_actions.clear()
        for cs in bd.calculation_setups:
            action = actions.CSOpen.get_QAction(cs)
            action.setText(cs)
            self.cs_actions.append(action)
            self.addAction(action)


# class ToolsMenu(QtWidgets.QMenu):
#     """
#     Tools Menu: contains actions in regard to special tooling aspects of the AB
#     """
#
#     def __init__(self, parent=None) -> None:
#         super().__init__(parent)
#         self.setTitle("&Tools")
#
#         self.manage_plugins_action = actions.PluginWizardOpen.get_QAction()
#
#         self.addAction(self.manage_plugins_action)


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
            "&About Qt", lambda: QtWidgets.QMessageBox.aboutQt(application.main_window)
        )
        self.addAction(
            qicons.question, "&Get help on the wiki", self.open_wiki
        )
        self.addAction(
            qicons.issue, "&Report an idea/issue on GitHub", self.raise_issue_github
        )

    def about(self):
        """Displays an 'about' window to the user containing e.g. the version of the AB and copyright info"""
        # set the window text in html format
        text = f"""
        Activity Browser - a graphical interface for Brightway2.<br><br>
        Application version: <b>{version("activity_browser")}</b><br>
        bw2data version: <b>{version("bw2data")}</b><br>
        bw2io version: <b>{version("bw2calc")}</b><br>
        bw2calc version: <b>{version("bw2io")}</b><br><br>
        All development happens on <a href="https://github.com/LCA-ActivityBrowser/activity-browser">github</a>.<br><br>
        For copyright information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/tree/main#copyright">this page</a>.<br><br>
        For license information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt">this page</a>.<br><br>
        """

        # set up the window
        about_window = QtWidgets.QMessageBox(parent=application.main_window)
        about_window.setWindowTitle("About the Activity Browser")
        about_window.setIconPixmap(qicons.ab.pixmap(QSize(150, 150)))
        about_window.setText(text)

        # execute
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
        self.setTitle("Open project")
        self.populate()

        self.aboutToShow.connect(self.populate)
        self.triggered.connect(lambda act: actions.ProjectSwitch.run(act.data()))

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
                application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning) if not bw_25 else qicons.empty)

            self.addAction(action)


class ImportDatabaseMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Import database")
        self.setIcon(qicons.import_db)

        self.import_from_ecoinvent_action = actions.DatabaseImportFromEcoinvent.get_QAction()
        self.import_from_excel_action = actions.DatabaseImporterExcel.get_QAction()
        self.import_from_bw2package_action = actions.DatabaseImporterBW2Package.get_QAction()

        self.import_from_ecoinvent_action.setText("ecoinvent...")
        self.import_from_excel_action.setText("from .xlsx")
        self.import_from_bw2package_action.setText("from .bw2package")

        self.addAction(self.import_from_excel_action)
        self.addAction(self.import_from_bw2package_action)
        self.addSeparator()
        self.addAction(self.import_from_ecoinvent_action)


class ImportICMenu(QtWidgets.QMenu):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Import impact categories")
        self.setIcon(qicons.import_db)

        self.beta_warning = QtWidgets.QWidgetAction(self)
        self.beta_warning.setDefaultWidget(QtWidgets.QLabel("Beta features, use at your own risk"))

        self.import_from_ei_excel_action = actions.MethodImporterEcoinvent.get_QAction()
        self.import_from_bw2io_action = actions.MethodImporterBW2IO.get_QAction()

        self.import_from_ei_excel_action.setText("from ecoinvent excel")
        self.import_from_bw2io_action.setText("from bw2io")

        self.import_from_ei_excel_action.setIcon(QtGui.QIcon())
        self.import_from_bw2io_action.setIcon(QtGui.QIcon())

        self.addAction(self.beta_warning)
        self.addSeparator()
        self.addAction(self.import_from_ei_excel_action)
        self.addAction(self.import_from_bw2io_action)
