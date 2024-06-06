import bw2data as bd
from activity_browser import actions, application
from PySide2 import QtWidgets
from activity_browser.ui.widgets.dialog import DatabaseLinkingDialog
from activity_browser.actions.database.database_duplicate import DuplicateDatabaseDialog
from activity_browser.ui.wizards.db_export_wizard import DatabaseExportWizard
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard


def test_database_delete(ab_app, monkeypatch):
    db = "db_to_delete"

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'question',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    )

    assert bd.projects.current == "default"
    assert db in bd.databases

    actions.DatabaseDelete.run(db)

    assert db not in bd.databases


def test_database_duplicate(ab_app, monkeypatch, qtbot):
    db = "db_to_duplicate"
    dup_db = "db_that_is_duplicated"

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('db_that_is_duplicated', True))
    )

    assert bd.projects.current == "default"
    assert db in bd.databases
    assert dup_db not in bd.databases

    actions.DatabaseDuplicate.run(db)

    dialog = application.main_window.findChild(DuplicateDatabaseDialog)
    with qtbot.waitSignal(dialog.thread.finished, timeout=60*1000):
        pass

    assert db in bd.databases
    assert dup_db in bd.databases


def test_database_export(ab_app):
    # TODO: implement when we've redone the export wizard and actions
    actions.DatabaseExport.run()

    wizard = application.main_window.findChild(DatabaseExportWizard)
    assert wizard.isVisible()
    wizard.destroy()
    return


def test_database_import(ab_app):
    # TODO: implement when we've redone the import wizard and actions
    actions.DatabaseImport.run()

    wizard = application.main_window.findChild(DatabaseImportWizard)
    assert wizard.isVisible()
    wizard.destroy()
    return


def test_database_new(ab_app, monkeypatch):
    new_db = "db_that_is_new"

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('db_that_is_new', True))
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'information',
        staticmethod(lambda *args, **kwargs: True)
    )

    assert bd.projects.current == "default"
    assert new_db not in bd.databases

    actions.DatabaseNew.run()

    assert new_db in bd.databases

    db_number = len(bd.databases)

    actions.DatabaseNew.run()

    assert db_number == len(bd.databases)


def test_database_relink(ab_app, monkeypatch):
    db = "db_to_relink"
    from_db = "db_to_relink_from"
    to_db = "db_to_relink_to"

    monkeypatch.setattr(
        DatabaseLinkingDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: DatabaseLinkingDialog.Accepted)
    )

    monkeypatch.setattr(
        DatabaseLinkingDialog, 'relink',
        {"db_to_relink_from": "db_to_relink_to"}
    )

    assert db in bd.databases
    assert from_db in bd.databases
    assert to_db in bd.databases
    assert from_db in bd.Database(db).find_dependents()
    assert to_db not in bd.Database(db).find_dependents()

    actions.DatabaseRelink.run(db)

    assert db in bd.databases
    assert from_db in bd.databases
    assert to_db in bd.databases
    assert from_db not in bd.Database(db).find_dependents()
    assert to_db in bd.Database(db).find_dependents()
