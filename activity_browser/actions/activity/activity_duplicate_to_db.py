from typing import List

from qtpy import QtWidgets

import bw2data as bd
import bw_functional as bf

from activity_browser import application
from activity_browser.bwutils import refresh_node
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from .activity_open import ActivityOpen


class ActivityDuplicateToDB(ABAction):
    icon = qicons.duplicate_to_other_database
    text = "Duplicate to other database"

    @classmethod
    @exception_dialogs
    def run(cls, nodes: List[tuple | int | bd.Node], to_db_name: str = None):
        nodes = [refresh_node(node) for node in nodes]
        dbs = {node.get("database") for node in nodes}
        from_db_name = next(iter(dbs))
        from_db_backend = bd.databases[from_db_name]["backend"]

        if not len(dbs) == 1:
            raise ValueError("All selected activities must be from the same database.")

        if any([isinstance(node, bf.Product) for node in nodes]):
            raise ValueError("Products cannot be duplicated to another database. Duplicate the parent process instead.")

        if to_db_name:
            if not cls.confirm_db(to_db_name):
                return
        else:
            to_db_name = cls.request_db(from_db_name)

        to_db_backend = bd.databases[to_db_name]["backend"]

        if from_db_backend == to_db_backend:
            new_nodes = cls.duplicate_simple(nodes, to_db_name)
        elif from_db_backend == "sqlite" and to_db_backend == "functional_sqlite":
            new_nodes = cls.duplicate_sqlite_to_functional_sqlite(nodes, to_db_name)
        elif from_db_backend == "functional_sqlite" and to_db_backend == "sqlite":
            new_nodes = cls.duplicate_functional_sqlite_to_sqlite(nodes, to_db_name)
        else:
            raise NotImplementedError(f"Moving from {from_db_backend} to {to_db_backend} is not supported.")

        ActivityOpen.run(new_nodes)

    @staticmethod
    def request_db(from_db_name: str) -> str | None:
        # get valid databases (not the original database, or locked databases)
        target_dbs = [
            db_name for db_name, meta in bd.databases.items() if
            db_name != from_db_name
            and meta.get("read_only", True) is not True
        ]

        # return if there are no valid databases to duplicate to
        if not target_dbs:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only).",
            )
            return

        # construct a dialog where the user can choose a database to duplicate to
        target_db, ok = QtWidgets.QInputDialog.getItem(
            application.main_window,
            "Move node to database",
            "Target database:",
            target_dbs,
            0,
            False,
        )

        return target_db if ok else None

    @staticmethod
    def confirm_db(to_db_name: str):
        user_choice = QtWidgets.QMessageBox.question(
            application.main_window,
            "Move to new database",
            f"Move to {to_db_name} and open as new tab?",
        )
        return user_choice == user_choice.Yes

    @staticmethod
    def duplicate_simple(nodes: list[bd.Node], to_db_name: str) -> list[bd.Node]:
        new_nodes = []

        # move all supplied nodes to the db by copying them
        for node in nodes:
            new_node = node.copy(database=to_db_name)
            new_nodes.append(new_node)

        return new_nodes

    @staticmethod
    def duplicate_sqlite_to_functional_sqlite(nodes: list[bd.Node], to_db_name: str) -> list[bd.Node]:
        from bw_functional.convert import SQLiteToFunctionalSQLite
        new_nodes = []

        for node in nodes:
            dataset = node.as_dict()

            dataset.pop("id", None)
            dataset.pop("key", None)

            dataset["exchanges"] = [exc.as_dict() for exc in node.exchanges()]
            dataset["database"] = to_db_name  # because we didn't copy the dict this will also be reflected in node.key

            new_datasets = SQLiteToFunctionalSQLite.convert_process(node.key, dataset, False)
            new_exchanges = [x for ds in new_datasets.values() for x in ds.pop("exchanges", [])]

            for key, new_dataset in new_datasets.items():
                new_node = bd.Node(**new_dataset)
                new_node.save()
                new_nodes.append(new_node)

            for exc in new_exchanges:
                exc["output"] = (to_db_name, exc["output"][1])  # relink output to new db
                new_exc = bd.Edge(**exc)
                new_exc.save()

        return new_nodes

    @staticmethod
    def duplicate_functional_sqlite_to_sqlite(nodes: list[bd.Node], to_db_name: str) -> list[bd.Node]:
        raise NotImplementedError("Duplicating from functional_sqlite to sqlite is not yet implemented.")