import brightway2 as bw
from activity_browser import actions
from PySide2 import QtWidgets
from activity_browser.ui.widgets.dialog import DatabaseLinkingDialog


def test_database_delete(ab_app, monkeypatch):
    db = "db_to_delete"

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'question',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    )

    assert bw.projects.current == "default"
    assert db in bw.databases

    actions.DatabaseDelete(db, None).trigger()

    assert db not in bw.databases


def test_database_duplicate(ab_app, monkeypatch, qtbot):
    db = "db_to_duplicate"
    dup_db = "db_that_is_duplicated"

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('db_that_is_duplicated', True))
    )

    assert bw.projects.current == "default"
    assert db in bw.databases
    assert dup_db not in bw.databases

    action = actions.DatabaseDuplicate(db, None)
    action.trigger()

    with qtbot.waitSignal(action.dialog.thread.finished, timeout=60*1000):
        pass

    assert db in bw.databases
    assert dup_db in bw.databases


def test_database_export(ab_app):
    # TODO: implement when we've redone the export wizard and actions
    action = actions.DatabaseExport(None)
    action.trigger()
    assert action.wizard.isVisible()
    action.wizard.destroy()
    return


def test_database_import(ab_app):
    # TODO: implement when we've redone the import wizard and actions
    action = actions.DatabaseImport(None)
    action.trigger()
    assert action.wizard.isVisible()
    action.wizard.destroy()
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

    assert bw.projects.current == "default"
    assert new_db not in bw.databases

    actions.DatabaseNew(None).trigger()

    assert new_db in bw.databases

    db_number = len(bw.databases)

    actions.DatabaseNew(None).trigger()

    assert db_number == len(bw.databases)


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

    assert db in bw.databases
    assert from_db in bw.databases
    assert to_db in bw.databases
    assert from_db in bw.Database(db).find_dependents()
    assert to_db not in bw.Database(db).find_dependents()

    actions.DatabaseRelink(db, None).trigger()

    assert db in bw.databases
    assert from_db in bw.databases
    assert to_db in bw.databases
    assert from_db not in bw.Database(db).find_dependents()
    assert to_db in bw.Database(db).find_dependents()
