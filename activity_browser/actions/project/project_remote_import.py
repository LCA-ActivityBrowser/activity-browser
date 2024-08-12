from typing import Any
from PySide2 import QtWidgets, QtCore

from bw2io import install_project
import requests

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.logger import log
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.style import header


class CatalogueModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = []
        self._sorted = [key for key in self._data]

    def populate(self, data: dict) -> None:
        self._data = data
        self._sorted = [key for key in self._data]

    def data(self, index: int, role: int):
        if role == QtCore.Qt.DisplayRole:
            return self._sorted[index.row()]
        elif role == QtCore.Qt.ToolTipRole:
            return self._data[self._sorted[index.row()]]

    def rowCount(self, index: int) -> int:
        return len(self._data)

    def columnCount(self, index: int) -> int:
        return 1

    def headerData(self, section:int, orientation:QtCore.Qt.Orientation, role: int=QtCore.Qt.DisplayRole) -> Any:
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return "Available projects"
        return None


class CatalogueTable(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

        self.model = CatalogueModel()
        self.setModel(self.model)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.verticalHeader().setVisible(False)
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.table_name = "Available projects"
        # Make sure the selected projects is still visible after the focus leaves the table
        self.setStyleSheet("QTableView:!active {selection-background-color: lightgray;}")

    def populate(self, url: str) -> None:
        try:
            self.model.populate(requests.get(url).json())
        except:
            self.model.populate({"Error": None})
        self.model.layoutChanged.emit()


class ProjectRemoteImportWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Import project from remote server")
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
        )

        layout = QtWidgets.QVBoxLayout()

        remote_url_layout = QtWidgets.QHBoxLayout()
        remote_url_layout.setAlignment(QtCore.Qt.AlignLeft)
        remote_url_layout.addWidget(header("Remote URL:"))
        self.remote_url_path = QtWidgets.QLineEdit()
        self.remote_url_path.setText("https://files.brightway.dev/")
        remote_url_layout.addWidget(self.remote_url_path)
        layout.addLayout(remote_url_layout)

        remote_catalogue_layout = QtWidgets.QHBoxLayout()
        remote_catalogue_layout.setAlignment(QtCore.Qt.AlignLeft)
        remote_catalogue_layout.addWidget(header("Catalogue file:"))
        self.remote_catalogue = QtWidgets.QLineEdit()
        self.remote_catalogue.setText("projects-config.json")
        remote_catalogue_layout.addWidget(self.remote_catalogue)
        layout.addLayout(remote_catalogue_layout)

        refresh_button_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Download catalogue")
        refresh_button_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self._populate_table)
        layout.addLayout(refresh_button_layout)

        self.table = CatalogueTable()
        self._populate_table()
        self.table.selectionModel().selectionChanged.connect(
            self._handle_table_selection_changed
        )
        layout.addWidget(self.table)

        project_name_layout = QtWidgets.QHBoxLayout()
        project_name_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_name_layout.addWidget(header("Project name:"))
        self.project_name = QtWidgets.QLineEdit()
        self.project_name.setText("")
        self.project_name.textChanged.connect(self._handle_project_name_changed)
        project_name_layout.addWidget(self.project_name)
        layout.addLayout(project_name_layout)

        self._overwrite_checkbox = QtWidgets.QCheckBox("Overwrite existing project")
        self._overwrite_checkbox.clicked.connect(self._handle_overwrite_clicked)
        self._overwrite_checkbox.setEnabled(False)
        layout.addWidget(self._overwrite_checkbox)

        import_button_layout = QtWidgets.QHBoxLayout()
        self.import_button = QtWidgets.QPushButton("Create project")
        import_button_layout.addWidget(self.import_button)
        # Can not import until nothing is selected
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self._import_project)
        layout.addLayout(import_button_layout)

        self.setLayout(layout)

    def _populate_table(self):
        url_path = self.remote_url_path.text()
        if url_path[-1] != "/":
            url_path += "/"
        self.table.populate(url_path + self.remote_catalogue.text())

    def _selected_project_name(self) -> str:
        """Return the selected project name."""
        selection = self.table.selectedIndexes()
        if selection:
            selected_item: QtCore.QModelIndex = selection[0]
            if selected_item.isValid():
                return selected_item.data()
        return ""

    def _project_name(self) -> str:
        """Return the user typed project name or, if empty, the selected one."""
        if self.project_name.text() == "":
            return self._selected_project_name()
        return self.project_name.text()

    def _handle_table_selection_changed(self):
        """
        Update the UI when the table selection changes.

        We set the currently selected project name as placeholder text,
        to hint that it can be changed, or will be used as default.
        """
        self.project_name.setPlaceholderText(self._selected_project_name())
        self._check_project_already_exists()

    def _handle_project_name_changed(self):
        self._check_project_already_exists()

    def _handle_overwrite_clicked(self, checked: bool):
        self.import_button.setEnabled(checked)

    def _check_project_already_exists(self):
        """
        Update the overwrite checkbox and import button based on the project name.

        If the project already exists, it can only be imported with the
        overwrite flag set. To make sure the user does not import it accidentaly,
        the flag is reset every time a name is selected which does not exist.
        """
        if self._project_name() in bd.projects:
            self._overwrite_checkbox.setEnabled(True)
            self.import_button.setEnabled(False)
        else:
            self._overwrite_checkbox.setEnabled(False)
            self._overwrite_checkbox.setChecked(False)
            # Disable the import if there is no selection
            self.import_button.setEnabled(len(self.table.selectedIndexes()) > 0)

    def _import_project(self):
        """Import the selected project with the new name."""
        selection = self.table.selectedIndexes()
        if selection:
            selected_item: QtCore.QModelIndex = selection[0]
            if selected_item.isValid():
                original_name = self._selected_project_name()
                new_name = self._project_name()
                log.info(f"Importing project with name {new_name} "
                         f"(original name {original_name})")
                install_project(
                    original_name,
                    new_name,
                    url=self.remote_url_path.text(),
                    overwrite_existing=self._overwrite_checkbox.isChecked()
                )
                self.accept()
            else:
                log.error("Selected item for import invalid!")
        else:
            log.error("No project selected for import!")



class ProjectRemoteImport(ABAction):
    """
    ABAction to download a project file from a remote server.
    Allows for customization of server URL, created project name, and whether or not to overwrite existing projects.
    """

    icon = qicons.import_db
    text = "Import remote project"
    tool_tip = "Import a project file from a remote server"

    @staticmethod
    @exception_dialogs
    def run():
        window = ProjectRemoteImportWindow()
        window.adjustSize()
        window.exec_()
