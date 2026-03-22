from typing import List

from qtpy import QtCore, QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.strategies import relink_activity_exchanges
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ActivityRelink(ABAction):
    """
    ABAction to relink the exchanges of an activity to exchanges from another database.

    This action only uses the first key from activity_keys
    """

    icon = qicons.edit
    text = "Relink the activity exchanges"

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        # this action only uses the first key supplied to activity_keys
        key = activity_keys[0]

        # extract the brightway database and activity
        db = bd.Database(key[0])
        activity = bd.get_activity(key)

        # find the dependents for the database and construct the alternatives in tuple format
        depends = db.find_dependents()
        options = [(depend, list(bd.databases)) for depend in depends]

        # present the alternatives to the user in a linking dialog
        dialog = ActivityLinkingDialog.relink_sqlite(
            activity["name"], options, application.main_window
        )

        # return if the user cancels
        if dialog.exec_() == ActivityLinkingDialog.Rejected:
            return

        # relinking will take some time, set WaitCursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # use the relink_activity_exchanges strategy to relink the exchanges of the activity
        relinking_results = {}
        for old, new in dialog.relink.items():
            other = bd.Database(new)
            failed, succeeded, examples = relink_activity_exchanges(
                activity, old, other
            )
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        # restore normal cursor
        QtWidgets.QApplication.restoreOverrideCursor()

        # if any relinks failed present them to the user
        if failed > 0:
            relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(
                application.main_window, relinking_results, examples
            )
            relinking_dialog.exec_()


class ActivityLinkingDialog(QtWidgets.QDialog):
    """
    Displays the possible databases for relinking the exchanges for a given activity
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activity linking")

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
    ) -> "ActivityLinkingDialog":
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
        cls, act: str, options: list, parent=None
    ) -> "ActivityLinkingDialog":
        label = "Relinking exchanges from activity '{}'.".format(act)
        return cls.construct_dialog(label, options, parent)


class ActivityLinkingResultsDialog(QtWidgets.QDialog):
    """
    Provides a summary from a relinking of activity exchanges for the relinking of a
    single activity.
    A simple design layout based on the DatabaseLinkingResultsDialog
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
    ) -> "ActivityLinkingResultsDialog":
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
    ) -> "ActivityLinkingResultsDialog":
        return cls.construct_results_dialog(parent, link_results, unlinked_exchanges)

    def select_activity_to_open(self, actvty: tuple) -> None:
        if actvty in self.activityToOpen:
            self.activityToOpen.discard(actvty)
        self.activityToOpen.add(actvty)

    def open_activity(self):
        return self.activityToOpen

