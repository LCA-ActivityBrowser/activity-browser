import os
from importlib.metadata import version

from PySide2 import QtGui, QtWidgets
from PySide2.QtCore import QSize, QUrl, Slot

from activity_browser import actions, signals, application, info
from activity_browser.i18n import _
from activity_browser.mod import bw2data as bd

from .icons import qicons

AB_BW25 = True if os.environ.get("AB_BW25", False) else False

# Keep menu signal payloads independent from translated action labels.  The
# values mirror ``layouts.panels.panel.TabId`` without importing the layouts
# package here (which would introduce an import cycle while MainWindow loads).
GRAPH_EXPLORER_TAB_ID = "right.graph_explorer"
HISTORY_TAB_ID = "left.history"
WELCOME_TAB_ID = "right.welcome"


class MenuBar(QtWidgets.QMenuBar):
    """
    Main menu bar at the top of the Activity Browser window. Contains submenus for different user interaction categories
    """
    def __init__(self, window):
        super().__init__(parent=window)

        self.addMenu(ProjectMenu(self))
        self.addMenu(ViewMenu(self))
        self.addMenu(ToolsMenu(self))
        self.addMenu(HelpMenu(self))


class ProjectMenu(QtWidgets.QMenu):
    """
    Project menu: contains actions related to managing the project, such as project duplication, database importing etc.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle(_("&Project"))

        self.new_proj_action = actions.ProjectNew.get_QAction()
        self.dup_proj_action = actions.ProjectDuplicate.get_QAction()
        self.delete_proj_action = actions.ProjectDelete.get_QAction()

        self.import_proj_action = actions.ProjectImport.get_QAction()
        self.export_proj_action = actions.ProjectExport.get_QAction()

        self.import_db_action = actions.DatabaseImport.get_QAction()
        self.export_db_action = actions.DatabaseExport.get_QAction()
        self.update_biosphere_action = actions.BiosphereUpdate.get_QAction()

        self.manage_settings_action = actions.SettingsWizardOpen.get_QAction()

        self.addMenu(ProjectSelectionMenu(self))
        self.addAction(self.new_proj_action)
        self.addAction(self.dup_proj_action)
        self.addAction(self.delete_proj_action)
        self.addSeparator()
        self.addAction(self.import_proj_action)
        self.addAction(self.export_proj_action)
        self.addSeparator()
        self.addAction(self.import_db_action)
        self.addAction(self.export_db_action)
        self.addAction(self.update_biosphere_action)
        self.addSeparator()
        self.addMenu(MigrationsMenu(self))
        self.addSeparator()
        self.addAction(self.manage_settings_action)

        bd.projects.current_changed.connect(self.biosphere_exists)
        bd.databases.metadata_changed.connect(self.biosphere_exists)

    def biosphere_exists(self) -> None:
        """Test if the default biosphere exists as a database in the project"""
        exists = True if bd.config.biosphere in bd.databases else False
        self.update_biosphere_action.setEnabled(exists)
        self.import_db_action.setEnabled(exists)


class ViewMenu(QtWidgets.QMenu):
    """
    View menu: contains actions in regard to hiding and showing specific UI elements.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle(_("&View"))

        self.addAction(
            qicons.graph_explorer,
            _("&Graph Explorer"),
            lambda: signals.toggle_show_or_hide_tab.emit(GRAPH_EXPLORER_TAB_ID),
        )
        self.addAction(
            qicons.history,
            _("&Activity History"),
            lambda: signals.toggle_show_or_hide_tab.emit(HISTORY_TAB_ID),
        )
        self.addAction(
            qicons.welcome,
            _("&Welcome screen"),
            lambda: signals.toggle_show_or_hide_tab.emit(WELCOME_TAB_ID),
        )


class ToolsMenu(QtWidgets.QMenu):
    """
    Tools Menu: contains actions in regard to special tooling aspects of the AB
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle(_("&Tools"))

        self.manage_plugins_action = actions.PluginWizardOpen.get_QAction()

        self.addAction(self.manage_plugins_action)


class HelpMenu(QtWidgets.QMenu):
    """
    Help Menu: contains actions that show info to the user or redirect them to online resources
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle(_("&Help"))

        self.addAction(
            qicons.ab, _("&About Activity Browser"), self.about
        )
        self.addAction(
            _("&About Qt"),
            lambda: QtWidgets.QMessageBox.aboutQt(application.main_window),
        )
        self.addAction(
            qicons.question, _("&Get help on the wiki"), self.open_wiki
        )
        self.addAction(
            qicons.issue,
            _("&Report an idea/issue on GitHub"),
            self.raise_issue_github,
        )

    def about(self):
        """Displays an 'about' window to the user containing e.g. the version of the AB and copyright info"""
        # set the window text in html format
        text = _(
            "Activity Browser - a graphical interface for Brightway2.<br><br>"
            "Application version: <b>{application_version}</b><br>"
            "bw2data version: <b>{bw2data_version}</b><br>"
            "bw2io version: <b>{bw2io_version}</b><br>"
            "bw2calc version: <b>{bw2calc_version}</b><br><br>"
            "All development happens on <a href=\"https://github.com/LCA-ActivityBrowser/activity-browser\">github</a>.<br><br>"
            "For copyright information please see the copyright on <a href=\"https://github.com/LCA-ActivityBrowser/activity-browser/tree/main#copyright\">this page</a>.<br><br>"
            "For license information please see the copyright on <a href=\"https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt\">this page</a>.<br><br>",
            application_version=version("activity_browser"),
            bw2data_version=version("bw2data"),
            bw2io_version=version("bw2calc"),
            bw2calc_version=version("bw2io"),
        )

        # set up the window
        about_window = QtWidgets.QMessageBox(parent=application.main_window)
        about_window.setWindowTitle(_("About the Activity Browser"))
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
        self.setTitle(_("Open project"))
        self.populate()

        self.aboutToShow.connect(self.populate)
        self.triggered.connect(lambda act: bd.projects.set_current(act.text()))

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

            # add BW25 decorations if necessary
            name = proj.name if not bw_25 or AB_BW25 else "[BW25] " + proj.name

            # create the action and disable it if it's BW25 and BW25 is not supported
            action = QtWidgets.QAction(name, self)
            action.setEnabled(not bw_25 or AB_BW25)

            self.addAction(action)


class MigrationsMenu(QtWidgets.QMenu):
    """Menu that shows actions that regard to brightway migrations"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setTitle(_("Migrations"))
        self.install_migrations_action = actions.MigrationsInstall.get_QAction()

        self.addAction(self.install_migrations_action)
