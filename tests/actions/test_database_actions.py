import bw2data as bd
from qtpy import QtWidgets

from activity_browser import actions, application


def test_database_delete(monkeypatch, basic_database):
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    actions.DatabaseDelete.run(basic_database.name)

    assert basic_database.name not in bd.databases


def test_database_duplicate(monkeypatch, qtbot, basic_database):
    from activity_browser.actions.database.database_duplicate import DuplicateDatabaseDialog

    dup_db = "db_that_is_duplicated"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (dup_db, True)),
    )

    assert dup_db not in bd.databases

    actions.DatabaseDuplicate.run(basic_database.name)

    dialog = application.main_window.findChild(DuplicateDatabaseDialog)
    with qtbot.waitSignal(dialog.dup_thread.finished, timeout=60 * 1000):
        pass

    assert basic_database.name in bd.databases
    assert dup_db in bd.databases


def test_database_export(main_window):
    # TODO: implement when we've redone the export wizard and actions
    from activity_browser.ui.wizards.db_export_wizard import DatabaseExportWizard

    actions.DatabaseExport.run()

    wizard = main_window.findChild(DatabaseExportWizard)
    assert wizard.isVisible()
    wizard.destroy()


def test_database_new(monkeypatch, basic_database):
    from activity_browser.actions.database.database_new import NewDatabaseDialog

    new_db = "db_that_is_new"

    monkeypatch.setattr(
        NewDatabaseDialog,
        "get_new_database_data",
        staticmethod(lambda *args, **kwargs: (new_db, "functional_sqlite", True)),
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert new_db not in bd.databases

    actions.DatabaseNew.run()

    assert new_db in bd.databases

    db_number = len(bd.databases)

    actions.DatabaseNew.run()

    assert db_number == len(bd.databases)
#
#
# def test_database_relink(ab_app, monkeypatch):
#     db = "db_to_relink"
#     from_db = "db_to_relink_from"
#     to_db = "db_to_relink_to"
#
#     monkeypatch.setattr(
#         DatabaseLinkingDialog,
#         "exec_",
#         staticmethod(lambda *args, **kwargs: DatabaseLinkingDialog.Accepted),
#     )
#
#     monkeypatch.setattr(
#         DatabaseLinkingDialog, "relink", {"db_to_relink_from": "db_to_relink_to"}
#     )
#
#     assert db in databases
#     assert from_db in databases
#     assert to_db in databases
#     assert from_db in Database(db).find_dependents()
#     assert to_db not in Database(db).find_dependents()
#
#     actions.DatabaseRelink.run(db)
#
#     assert db in databases
#     assert from_db in databases
#     assert to_db in databases
#     assert from_db not in Database(db).find_dependents()
#     assert to_db in Database(db).find_dependents()
