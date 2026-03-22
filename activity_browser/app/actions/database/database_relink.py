from qtpy import QtCore, QtWidgets

import bw2data as bd
from bw2data.backends import ExchangeDataset, sqlite3_lci_db

from activity_browser.app import application, metadata
from activity_browser.app.actions.base import ABAction, exception_dialogs
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

        depends = ExchangeDataset.select(ExchangeDataset.input_database).where(ExchangeDataset.output_database == db_name)
        depends = set([d.input_database for d in depends if d.input_database != db_name])

        # find the dependencies of the database and construct a list of suitable candidates
        options = [(depend, list(bd.databases)) for depend in depends]

        # construct a dialog in which the user chan choose which depending database to connect to which candidate
        dialog = DatabaseLinkingDialog.relink_sqlite(
            db_name, options, application.main_window
        )

        # return if the user cancels
        if dialog.exec_() != DatabaseLinkingDialog.Accepted:
            return

        linking_dict = {k: v for k, v in dialog.links.items() if k != v}

        if not linking_dict:
            return

        relink_keys = DatabaseRelink.get_input_keys(db_name, list(linking_dict.keys()))
        datasets = metadata.get_metadata(relink_keys, ["name", "product", "unit", "categories", "location"])

        relink_key_map = {}
        for ds in datasets.itertuples():
            key = ds.Index
            database = linking_dict.get(key[0])
            match = metadata.match(
                name=ds.name,
                product=ds.product,
                unit=ds.unit,
                categories=ds.categories,
                location=ds.location,
                database=database,
            )

            if not len(match) == 1:
                raise Exception(f"Could not uniquely relink exchange from {key} in database {database}")

            relink_key_map[key] = match.index[0]

        DatabaseRelink.set_input_keys(db_name, relink_key_map)

        QtWidgets.QMessageBox.information(
            application.main_window,
            "Database relinked",
            f"Successfully relinked database '{db_name}'."
        )

    @staticmethod
    def get_input_keys(output_db: str, db_list: list[str]) -> list[tuple[str, str]]:
        return list(
            (
                ExchangeDataset
                .select(ExchangeDataset.input_database, ExchangeDataset.input_code)
                .where(
                    (ExchangeDataset.output_database == output_db) &
                    (ExchangeDataset.input_database << db_list)
                )
            ).tuples()
        )

    @staticmethod
    def set_input_keys(output_db: str, key_map: dict[tuple[str, str], tuple[str, str]]) -> None:
        with sqlite3_lci_db.db.atomic():
            for old_key, new_key in key_map.items():
                ExchangeDataset.update(
                    input_database=new_key[0],
                    input_code=new_key[1]
                ).where(
                    (ExchangeDataset.output_database == output_db) &
                    (ExchangeDataset.input_database == old_key[0]) &
                    (ExchangeDataset.input_code == old_key[1])
                ).execute()


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
        from activity_browser import app

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
                lambda: app.actions.ActivityOpen.run([act.key])
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

