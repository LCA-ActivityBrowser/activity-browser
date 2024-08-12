from PySide2 import QtWidgets, QtCore

import requests

from activity_browser.actions.base import ABAction, exception_dialogs
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

        # self.verticalHeader().setDefaultSectionSize(22)
        self.verticalHeader().setVisible(False)

        self.table_name = "Available projects"

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
        layout.addLayout(refresh_button_layout)

        self.table = CatalogueTable(self)
        self.table.populate("https://files.brightway.dev/projects-config.json")
        layout.addWidget(self.table)

        project_name_layout = QtWidgets.QHBoxLayout()
        project_name_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_name_layout.addWidget(header("Project name:"))
        self.project_name = QtWidgets.QLineEdit()
        self.project_name.setText("")
        project_name_layout.addWidget(self.project_name)
        layout.addLayout(project_name_layout)

        import_button_layout = QtWidgets.QHBoxLayout()
        self.import_button = QtWidgets.QPushButton("Create project")
        import_button_layout.addWidget(self.import_button)
        layout.addLayout(import_button_layout)

        self.setLayout(layout)


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
