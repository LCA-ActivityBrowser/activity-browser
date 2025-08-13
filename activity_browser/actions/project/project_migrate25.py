from tqdm import tqdm
from logging import getLogger
from qtpy import QtWidgets, QtGui, QtCore

import bw2data as bd
import pandas as pd

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import AB_metadata
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread

log = getLogger(__name__)


class ProjectMigrate25(ABAction):
    """
    ABAction to duplicate a project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Else, instructs the ProjectController to duplicate the current
    project to the new name.
    """

    icon = qicons.copy
    text = "Migrate project"
    tool_tip = "Migrate the project to bw25"

    @staticmethod
    @exception_dialogs
    def run(name: str = None):
        if name is None:
            name = bd.projects.current

        dialog = MigrateDialog(name, application.main_window)
        dialog.exec_()

        if dialog.result() == dialog.DialogCode.Rejected:
            return

        if name != bd.projects.current:
            bd.projects.set_current(name, update=False)

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=application.main_window,
            labelText="Migrating project, this may take a while...",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Migrating project to Brightway25")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        thread = MigrateThread(application)
        thread.finished.connect(lambda: progress.deleteLater())
        thread.start()
        thread.connect_progress_dialog(progress)


class MigrateDialog(QtWidgets.QDialog):
    def __init__(self, project_name: str, parent=None):
        from .project_export import ProjectExport

        super().__init__(parent)
        self.setWindowTitle("Migrate project")
        label = QtWidgets.QLabel(f"Migrate project ({project_name}) from legacy to Brightway25. This cannot be undone.")

        cancel = QtWidgets.QPushButton("Cancel")
        migrate = QtWidgets.QPushButton("Migrate")
        backup = ProjectExport.get_QButton(project_name)
        backup.setText("Back-up project")
        backup.setIcon(QtGui.QIcon())

        cancel.clicked.connect(self.reject)
        migrate.clicked.connect(self.accept)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(backup)
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(migrate)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(button_layout)

        self.setLayout(layout)


class MigrateThread(ABThread):
    def run_safely(self):
        self.pre_process_methods()

        log.info("Updating and processing all datasets in the project")
        bd.projects.set_current(bd.projects.current)

        for db_name in bd.databases:
            self.update_database_activity_types(db_name)

        # set the bw25 flag in the project dataset
        bd.projects.dataset.data["25"] = True
        bd.projects.dataset.save()

        # reloading project to ensure all changes are applied
        bd.projects.set_current(bd.projects.current)

    @classmethod
    def pre_process_methods(cls):
        log.info("Pre-processing methods for migration to bw25")
        data = {m: bd.Method(m).load() for m in bd.methods}
        df = pd.DataFrame([(k, v[0][0], v[0][1], v[1])
                           for k, values in data.items() for v in values
                           if isinstance(v[0], tuple) and len(v) == 2 and len(v[0]) == 2],
                          columns=["method", "database", "code", "value"])

        df = df.merge(AB_metadata.dataframe["id"], left_on=["database", "code"], right_index=True)

        signals.method.blockSignals(True)
        signals.meta.blockSignals(True)

        for name in tqdm(df["method"].unique(), desc="Pre-processing methods", unit="method", total=len(df["method"].unique())):
            method_df = df[df["method"] == name][["id", "value"]]
            method_list = list(method_df.itertuples(index=False, name=None))
            bd.Method(name).write(method_list, process=False)

        signals.method.blockSignals(False)
        signals.meta.blockSignals(False)

        return

    @classmethod
    def update_database_activity_types(cls, db_name: str):
        database = bd.Database(db_name)
        write = False

        if not isinstance(database, bd.backends.SQLiteBackend):
            return

        log.info(f"Updating activity types in {db_name}")
        raw = database.load()

        for key, ds in tqdm(raw.items(), desc=f"Updating activity types in {db_name}", unit="activity", total=len(raw)):
            if cls.activity_is_processwithreferenceproduct(ds):
                write = True
                ds["type"] = "processwithreferenceproduct"

        if write:
            database.write(raw)

    @staticmethod
    def activity_is_processwithreferenceproduct(ds: dict) -> bool:
        production = [exc for exc in ds.get("exchanges", []) if exc.get("type") == "production"]
        return (
            ds.get("type") in ["process", "processwithreferenceproduct"] and
            (
                len(production) == 0 or
                production[0].get("input") == (ds["database"], ds["code"])
            )
        )



