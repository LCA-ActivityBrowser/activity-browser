from typing import List

from qtpy import QtWidgets

import bw2data as bd

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
    def run(cls, nodes: List[tuple | int | bd.Node], to_db: str = None):
        nodes = [refresh_node(node) for node in nodes]

        dbs = {node.get("database") for node in nodes}
        if not len(dbs) == 1:
            raise ValueError("All selected activities must be from the same database.")
        from_db = next(iter(dbs))

        if to_db and not cls.confirm_db(to_db):
            return

        to_db = to_db or cls.request_db(nodes, backend=bd.databases[from_db]["backend"])

        if not to_db:
            return

        new_nodes = []

        # otherwise move all supplied nodes to the db by copying them
        for node in nodes:
            new_node = node.copy(database=to_db)
            new_nodes.append(new_node)

        ActivityOpen.run(new_nodes)

    @staticmethod
    def request_db(nodes: list[bd.Node], backend: str) -> str | None:
        # get valid databases (not the original database, locked databases, or databases with a different backend)
        origin_db = next(iter(nodes)).get("database")
        target_dbs = [
            db for db, meta in bd.databases.items() if
            db != origin_db
            and meta.get("read_only") is not True
            and meta.get("backend") == backend
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
    def confirm_db(to_db: str):
        user_choice = QtWidgets.QMessageBox.question(
            application.main_window,
            "Move to new database",
            f"Move to {to_db} and open as new tab?",
        )
        return user_choice == user_choice.Yes
