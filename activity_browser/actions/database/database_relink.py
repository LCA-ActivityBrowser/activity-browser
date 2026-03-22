from qtpy import QtCore, QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.strategies import relink_exchanges_existing_db
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class DatabaseRelink(ABAction):
    """
    ABAction to relink the dependencies of a database.
    """

    icon = qicons.edit
    text = "Relink the database"
    tool_tip = "Relink the dependencies of this database"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        db_name = db_name
        # get brightway database object
        db = bd.Database(db_name)

        # find the dependencies of the database and construct a list of suitable candidates
        depends = db.find_dependents()
        options = [(depend, list(bd.databases)) for depend in depends]

        # construct a dialog in which the user chan choose which depending database to connect to which candidate
        dialog = DatabaseLinkingDialog.relink_sqlite(
            db_name, options, application.main_window
        )

        # return if the user cancels
        if dialog.exec_() != DatabaseLinkingDialog.Accepted:
            return

        # else, start the relinking
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        relinking_results = dict()

        # relink using relink_exchanges_existing_db strategy
        for old, new in dialog.relink.items():
            other = bd.Database(new)
            failed, succeeded, examples = relink_exchanges_existing_db(db, old, other)
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        QtWidgets.QApplication.restoreOverrideCursor()

        # if any failed, present user with results dialog
        if failed > 0:
            relinking_dialog = DatabaseLinkingResultsDialog.present_relinking_results(
                application.main_window, relinking_results, examples
            )
            relinking_dialog.exec_()
            relinking_dialog.open_activity()


class DatabaseLinkingDialog(QtWidgets.QDialog):
    """Display all of the possible links in a single dialog for the user.

    Allow users to select alternate database links."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database linking")

        self.db_label = QtWidgets.QLabel()
        self.label_choices = []
        self.grid_box = QtWidgets.QGroupBox("Database links:")
        self.grid = QtWidgets.QGridLayout()
        self.grid_box.setLayout(self.grid)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.db_label)
        layout.addWidget(self.grid_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def relink(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.

        Only returns key/value pairs if they differ.
        """
        return {
            label.text(): combo.currentText()
            for label, combo in self.label_choices
            if label.text() != combo.currentText()
        }

    @property
    def links(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.
        """
        return {
            label.text(): combo.currentText() for label, combo in self.label_choices
        }

    @classmethod
    def construct_dialog(
        cls,
        label: str,
        options: list,
        parent: QtWidgets.QWidget = None,
    ) -> "DatabaseLinkingDialog":
        obj = cls(parent)
        obj.db_label.setText(label)
        # Start at 1 because row 0 is taken up by the db_label
        for i, item in enumerate(options):
            label = QtWidgets.QLabel(item[0])
            combo = QtWidgets.QComboBox()
            combo.addItems(item[1])
            combo.setCurrentText(item[0])
            obj.label_choices.append((label, combo))
            obj.grid.addWidget(label, i, 0, 1, 2)
            obj.grid.addWidget(combo, i, 2, 1, 2)
        obj.updateGeometry()
        return obj

    @classmethod
    def relink_sqlite(
        cls, db: str, options: list, parent=None
    ) -> "DatabaseLinkingDialog":
        label = "Relinking exchanges from database '{}'.".format(db)
        return cls.construct_dialog(label, options, parent)

    @classmethod
    def relink_bw2package(
        cls, options: list, parent=None
    ) -> "DatabaseLinkingDialog":
        label = (
            "Some database(s) could not be found in the current project,"
            " attempt to relink the exchanges to a different database?"
        )
        return cls.construct_dialog(label, options, parent)

    @classmethod
    def relink_excel(
        cls, options: list, parent=None
    ) -> "DatabaseLinkingDialog":
        label = "Customize database links for exchanges in the imported database."
        return cls.construct_dialog(label, options, parent)


class DatabaseLinkingResultsDialog(QtWidgets.QDialog):
    """To be used when relinking a database, this dialog will pop up if
    some of the exchanges in the database fail to be linked to the new
    database.
    Up to five of the unlinked activities are printed on the screen,

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Relinking database results")

        button = QtWidgets.QDialogButtonBox.Ok
        self.buttonBox = QtWidgets.QDialogButtonBox(button)
        self.buttonBox.accepted.connect(self.accept)
        self.databases_relinked = QtWidgets.QVBoxLayout()

        self.activityToOpen = set()

        self.exchangesUnlinked = QtWidgets.QVBoxLayout()

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.databases_relinked)
        self.layout.addLayout(self.exchangesUnlinked)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    @classmethod
    def construct_results_dialog(
        cls,
        parent: QtWidgets.QWidget = None,
        link_results: dict = None,
        unlinked_exchanges: dict = None,
    ) -> "DatabaseLinkingResultsDialog":
        from activity_browser import actions

        obj = cls(parent)
        for k, results in link_results.items():
            obj.databases_relinked.addWidget(
                QtWidgets.QLabel(f"{k} = {results[1]} successfully linked")
            )
            obj.databases_relinked.addWidget(
                QtWidgets.QLabel(f"{k} = {results[0]} flows failed to link")
            )

        obj.exchangesUnlinked.addWidget(
            QtWidgets.QLabel("Up to 5 unlinked exchanges (click to open)")
        )
        for act, key in unlinked_exchanges.items():
            button = QtWidgets.QPushButton(act.as_dict()["name"])
            button.clicked.connect(
                lambda: actions.ActivityOpen.run([act.key])
            )
            obj.exchangesUnlinked.addWidget(button)
        obj.updateGeometry()

        return obj

    @classmethod
    def present_relinking_results(
        cls,
        parent: QtWidgets.QWidget = None,
        link_results: dict = None,
        unlinked_exchanges: dict = None,
    ) -> "DatabaseLinkingResultsDialog":
        return cls.construct_results_dialog(parent, link_results, unlinked_exchanges)

    def select_activity_to_open(self, actvty: tuple) -> None:
        if actvty in self.activityToOpen:
            self.activityToOpen.discard(actvty)
        self.activityToOpen.add(actvty)

    def open_activity(self):
        return self.activityToOpen

