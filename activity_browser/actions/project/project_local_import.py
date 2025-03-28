import json
from tarfile import open as tar_open, TarFile, TarError
from logging import getLogger

from qtpy import QtWidgets, QtCore
from bw2io import restore_project_directory

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui import icons, widgets

log = getLogger(__name__)


class ProjectLocalImportWindow(QtWidgets.QDialog):

    MAX_PROJECT_NAME_JSON_SIZE = 1024
    PROJECT_FILE = ".project-name.json"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Import project from file")
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
        )

        layout = QtWidgets.QVBoxLayout()
        dialog_spacing = 8

        file_chooser_layout = QtWidgets.QHBoxLayout()
        file_chooser_layout.setAlignment(QtCore.Qt.AlignLeft)
        tarball_label = QtWidgets.QLabel("Project file:")
        self._selected_file_edit = QtWidgets.QLineEdit()
        self._selected_file_edit.setMinimumWidth(300)
        self._selected_file_edit.textChanged.connect(self._load_project_name)
        self._browse_button = QtWidgets.QPushButton("Browse")
        self._browse_button.clicked.connect(self._handle_browse_clicked)
        file_chooser_layout.addWidget(tarball_label)
        file_chooser_layout.addWidget(self._selected_file_edit)
        file_chooser_layout.addWidget(self._browse_button)

        layout.addLayout(file_chooser_layout)

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
        self._message_label = QtWidgets.QLabel()

        layout.addWidget(self._message_label)

        self.setLayout(layout)
        self._last_url = ""
        self._loaded_project_name = ""
        self._reset_dialog()
        self._message_label.setText("Select a project file")

    def _reset_dialog(self):
        self.project_name.setEnabled(False)
        self.project_name.setPlaceholderText("")
        self._overwrite_checkbox.setEnabled(False)
        self._overwrite_checkbox.setChecked(False)
        self._activate_project_checkbox.setEnabled(False)
        self.import_button.setEnabled(False)
        self._message_label.setText("")

    def _enable_ui(self):
        self.project_name.setEnabled(True)
        self.project_name.setPlaceholderText("")
        self._activate_project_checkbox.setEnabled(True)
        self._message_label.setText("")

    def _handle_browse_clicked(self):
        """Open a system file dialog and allow the user to select a file"""
        file = QtWidgets.QFileDialog().getOpenFileName(
            self,
            "Select archive file",
            filter = "Tar GZ (*.tar.gz)"
        )[0]
        # The returned value is None on Cancel
        if file:
            self._selected_file_edit.setText(QtCore.QDir.toNativeSeparators(file))
            self._load_project_name()

    def _decode_project_name(self, tar: TarFile):
        """
        Get the list of files from the TarFile, and decode the name
        from the .project-name.json.

        Updates the UI with error messages if it fails.
        """
        # all files in the archive
        name_list = tar.getnames()
        # list of files, where the path contains ".project-name.json"
        project_name_files = [name for name in name_list if self.PROJECT_FILE in name]
        if len(project_name_files) == 0:
            self._message_label.setText(
                f"No '{self.PROJECT_FILE}' file found in project file"
            )
            return
        if len(project_name_files) > 1:
            self._message_label.setText(
                f"More than one '{self.PROJECT_FILE}' file found in project file"
            )
            return
        # choose the first one, we expect to have only one
        project_name_file = project_name_files[0]
        # get TarInfo for it
        tar_info_project_name_file = tar.getmember(project_name_file)
        # prevent too big files from being extracted
        if tar_info_project_name_file.size > self.MAX_PROJECT_NAME_JSON_SIZE:
            self._message_label.setText(
                f"Size of '{self.PROJECT_FILE}' file is too "
                f"big: {tar_info_project_name_file.size}"
            )
            return
        # get extracter BufferedReader
        if extracter := tar.extractfile(project_name_file):
            try:
                # JSON should have a single string value with the key "name"
                project_name = json.loads(extracter.read())["name"]
            except:
                self._message_label.setText(
                    "Failed to decode project name"
                )
                return
            if project_name == "":
                self._message_label.setText("Decoded project name is empty")
                return
            self._enable_ui()
            self._loaded_project_name = project_name
            self.project_name.setPlaceholderText(self._loaded_project_name)
            self._check_project_already_exists()

    def _load_project_name(self):
        """Exception handling for the project name decoding."""
        try:
            self._reset_dialog()
            archive = self._selected_file_edit.text()
            tar = tar_open(archive, "r:gz")
        except FileNotFoundError:
            self._message_label.setText("Project file not found")
        except TarError:
            self._message_label.setText("Error opening project file")
        except (ValueError, OSError):
            self._message_label.setText("Select a project file")
        else:
            try:
                with tar:
                    self._decode_project_name(tar)
            except TarError:
                self._message_label.setText("Error opening project file")

    def _selected_project_name(self) -> str:
        """The name of the project as decoded from the tarball"""
        return self._loaded_project_name

    def _project_name(self) -> str:
        """Return the user typed project name or, if empty, the loaded one."""
        if self.project_name.text() == "":
            return self._selected_project_name()
        return self.project_name.text()

    def _handle_project_name_changed(self):
        """Trigger duplicate project name check"""
        self._check_project_already_exists()

    def _unique_project_update(self):
        """
        Update the UI when the entered project name is unique.
        """
        self.import_button.setEnabled(True)
        self._message_label.setText("")

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
            self._unique_project_update()

    def _import_project(self):
        """
        Import the selected project with the new name.
        It is checked with the UI flow, that there is a tarball loaded,
        and a unique name provided or the overwrite flag is set.
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

            restore_project_directory(
                self._selected_file_edit.text(),
                new_name,
                overwrite_existing=self._overwrite_checkbox.isChecked()
            )
            if self._activate_project_checkbox.isChecked():
                bd.projects.set_current(new_name)
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.accept()
        else:
            log.error(
                f"Project name ({new_name}) or "
                f"import name ({original_name}) is not valid."
            )


class ProjectLocalImport(ABAction):
    """
    ABAction to download a project file from a remote server.
    Allows for customization of server URL, created project name, and whether or not to overwrite existing projects.
    """

    icon = icons.qicons.import_db
    text = "Import local project"
    tool_tip = "Import a project file from a remote server"

    @staticmethod
    @exception_dialogs
    def run():
        window = ProjectLocalImportWindow()
        window.adjustSize()
        window.exec_()
