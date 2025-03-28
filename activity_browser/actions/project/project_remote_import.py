from typing import Any
from urllib.parse import urljoin
from logging import getLogger

from qtpy import QtWidgets, QtCore

from bw2io import install_project
import requests

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui import icons, widgets

log = getLogger(__name__)


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

    def populate(self, data: dict) -> None:
        self.model.populate(data)
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
        dialog_spacing = 8

        remote_url_layout = QtWidgets.QHBoxLayout()
        remote_url_layout.setAlignment(QtCore.Qt.AlignLeft)
        remote_url_layout.addWidget(widgets.ABLabel.demiBold("Remote URL:"))
        self.remote_url_path = QtWidgets.QLineEdit()
        self.remote_url_path.setText("https://files.brightway.dev/")
        self.remote_url_path.textChanged.connect(self._handle_url_changed)
        remote_url_layout.addWidget(self.remote_url_path)
        layout.addLayout(remote_url_layout)

        remote_catalogue_layout = QtWidgets.QHBoxLayout()
        remote_catalogue_layout.setAlignment(QtCore.Qt.AlignLeft)
        remote_catalogue_layout.addWidget(widgets.ABLabel.demiBold("Catalogue file:"))
        self.remote_catalogue = QtWidgets.QLineEdit()
        self.remote_catalogue.setText("projects-config.json")
        self.remote_catalogue.textChanged.connect(self._handle_url_changed)
        remote_catalogue_layout.addWidget(self.remote_catalogue)
        layout.addLayout(remote_catalogue_layout)
        layout.addSpacing(dialog_spacing)

        refresh_button_layout = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Download catalogue")
        refresh_button_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self._populate_table)
        layout.addLayout(refresh_button_layout)
        layout.addSpacing(dialog_spacing)

        self.table = CatalogueTable()
        self.table.selectionModel().selectionChanged.connect(
            self._handle_table_selection_changed
        )
        layout.addWidget(self.table)
        layout.addSpacing(dialog_spacing)

        project_name_layout = QtWidgets.QHBoxLayout()
        project_name_layout.setAlignment(QtCore.Qt.AlignLeft)
        project_name_layout.addWidget(widgets.ABLabel.demiBold("Project name:"))
        self.project_name = QtWidgets.QLineEdit()
        self.project_name.setText("")
        self.project_name.textChanged.connect(self._handle_project_name_changed)
        project_name_layout.addWidget(self.project_name)
        layout.addLayout(project_name_layout)

        self._overwrite_checkbox = QtWidgets.QCheckBox("Overwrite existing project")
        self._overwrite_checkbox.clicked.connect(self._handle_overwrite_clicked)
        layout.addWidget(self._overwrite_checkbox)

        self._activate_project_checkbox = QtWidgets.QCheckBox("Activate project after import")
        self._activate_project_checkbox.setChecked(True)
        layout.addWidget(self._activate_project_checkbox)

        import_button_layout = QtWidgets.QHBoxLayout()
        self.import_button = QtWidgets.QPushButton("Create project")
        import_button_layout.addWidget(self.import_button)
        self.import_button.clicked.connect(self._import_project)
        layout.addLayout(import_button_layout)
        self._message_label = QtWidgets.QLabel("")
        layout.addWidget(self._message_label)

        self.setLayout(layout)
        self._last_url = ""
        # Initialize the dialog
        self._populate_table()

    def _reset_dialog(self):
        self.table.setEnabled(False)
        self.table.populate(dict())
        self.table.selectionModel().clearSelection()
        self.project_name.setEnabled(False)
        self.project_name.setPlaceholderText("")
        self._overwrite_checkbox.setEnabled(False)
        self._overwrite_checkbox.setChecked(False)
        self._activate_project_checkbox.setEnabled(False)
        self.import_button.setEnabled(False)
        self._message_label.setText("")

    def url(self) -> str:
        return urljoin(self.remote_url_path.text(), self.remote_catalogue.text())

    def _populate_table(self):
        self._reset_dialog()
        try:
            self.refresh_button.setText("Downloading...")
            self.refresh_button.setEnabled(False)
            self.repaint()
            self.setCursor(QtCore.Qt.WaitCursor)
            self._last_url = self.url()
            data = requests.get(self._last_url).json()
            self.table.setEnabled(True)
            self.project_name.setEnabled(True)
            self._activate_project_checkbox.setEnabled(True)
            success = True
        except:
            data = {"Error loading catalogue": None}
            self._message_label.setText("Load a valid catalogue")
            success = False

        self.refresh_button.setText("Download catalogue")
        self.refresh_button.setEnabled(True)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.table.populate(data)
        if success:
            self._check_project_already_exists()

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

    def _handle_url_changed(self):
        if self._last_url != self.url():
            self._reset_dialog()
            self._message_label.setText("Load a valid catalogue")

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

    def _unique_project_selection_update(self, selection_valid: bool):
        """
        Update the UI when the selection in the table changes and the
        project name is unique.
        """
        if selection_valid:
            self.import_button.setEnabled(True)
            self._message_label.setText("")
        else:
            self.import_button.setEnabled(False)
            self._message_label.setText("Select a project to import")

    def _duplicate_project_checkbox_update(self):
        """
        Update the UI when the overwrite checkbox state changes and the
        project name is not unique.

        Use the actual state of the checkbox, because it is not
        called only from the checkbox click event.
        """
        if self._overwrite_checkbox.isChecked():
            self.import_button.setEnabled(True)
            self._message_label.setText("")
        else:
            self.import_button.setEnabled(False)
            self._message_label.setText("Project name already exists")

    def _handle_overwrite_clicked(self):
        self._duplicate_project_checkbox_update()

    def _check_project_already_exists(self):
        """
        Update the overwrite checkbox and import button based on the project name.

        If the project already exists, it can only be imported with the
        overwrite flag set. To make sure the user does not import it accidentaly,
        the flag is reset every time the selected project or the project name changes.
        """
        self._overwrite_checkbox.setChecked(False)
        if self._project_name() in bd.projects:
            self._overwrite_checkbox.setEnabled(True)
            self._duplicate_project_checkbox_update()
        else:
            self._overwrite_checkbox.setEnabled(False)
            # Disable the import if there is no selection
            self._unique_project_selection_update(len(self.table.selectedIndexes()) > 0)

    def _import_project(self):
        """
        Import the selected project with the new name.
        It is checked with the UI flow, that there is a catalogue loaded,
        a project to import selected and a unique name provided or the overwrite
        flag is set.
        """
        original_name = self._selected_project_name()
        new_name = self._project_name()
        if original_name and new_name:
            log.info(f"Importing project with name {new_name} "
                        f"(original name {original_name})")
            self.import_button.setText("Creating project...")
            self.import_button.setEnabled(False)
            self.repaint()
            self.setCursor(QtCore.Qt.WaitCursor)

            install_project(
                original_name,
                new_name,
                url=self.remote_url_path.text(),
                overwrite_existing=self._overwrite_checkbox.isChecked()
            )
            if self._activate_project_checkbox.isChecked():
                bd.projects.set_current(new_name)
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.accept()
        else:
            log.error(f"Project name ({new_name}) or import name ({original_name}) is not valid.")



class ProjectRemoteImport(ABAction):
    """
    ABAction to download a project file from a remote server.
    Allows for customization of server URL, created project name, and whether or not to overwrite existing projects.
    """

    icon = icons.qicons.import_db
    text = "Import remote project"
    tool_tip = "Import a project file from a remote server"

    @staticmethod
    @exception_dialogs
    def run():
        window = ProjectRemoteImportWindow()
        window.adjustSize()
        window.exec_()
