import bw2data as bd
from qtpy import QtWidgets

from activity_browser import app


def _confirm_delete(monkeypatch) -> None:
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )


def _broken_activity_parameter_groups() -> list[str]:
    """Groups the Parameters pane would label as broken."""
    from bw2data.parameters import ActivityParameter, Group

    reserved = {"project"} | set(bd.databases.list)
    broken = []
    for group in Group.select():
        if group.name in reserved:
            continue
        if not ActivityParameter.select().where(
            ActivityParameter.group == group.name
        ).exists():
            broken.append(group.name)
    return broken


def test_database_delete(monkeypatch, basic_database):
    _confirm_delete(monkeypatch)

    app.actions.DatabaseDelete.run([basic_database.name])

    assert basic_database.name not in bd.databases


def test_database_delete_removes_functional_units(monkeypatch, basic_database):
    cs_name = "basic_calculation_setup"
    assert bd.calculation_setups[cs_name]["inv"]

    _confirm_delete(monkeypatch)
    app.actions.DatabaseDelete.run([basic_database.name])

    assert bd.calculation_setups[cs_name]["inv"] == []
    assert bd.calculation_setups[cs_name]["inv_active"] == []


def test_database_delete_removes_characterization_factors(monkeypatch, basic_database):
    from activity_browser.bwutils.characterization_factors import impact_methods_with_flows

    elementary = basic_database.get("elementary")
    assert impact_methods_with_flows({elementary.id})

    _confirm_delete(monkeypatch)
    app.actions.DatabaseDelete.run([basic_database.name])

    assert not impact_methods_with_flows({elementary.id})


def test_database_delete_clears_orphan_activity_parameter_groups(monkeypatch, basic_database):
    """Deleting a DB must not leave hashed activity parameter groups behind."""
    from bw2data.parameters import ActivityParameter
    from fixtures.database_roundtrip import write_source_db

    _confirm_delete(monkeypatch)

    db_name = "db_with_params"
    write_source_db(db_name, "sqlite", parameters=True)

    activity_groups = {
        row.group
        for row in ActivityParameter.select(ActivityParameter.group).where(
            ActivityParameter.database == db_name
        )
    }
    assert activity_groups
    assert db_name not in activity_groups

    app.actions.DatabaseDelete.run([db_name])

    assert db_name not in bd.databases
    assert not ActivityParameter.select().where(
        ActivityParameter.database == db_name
    ).exists()
    assert _broken_activity_parameter_groups() == []


def test_fix_broken_groups_removes_orphan_activity_groups(basic_database):
    """Brightway removes parameter rows on delete; AB must drop the leftover groups."""
    from bw2data.parameters import ActivityParameter, Group
    from activity_browser.app.actions.parameter.parameter_modify import ParameterModify
    from fixtures.database_roundtrip import write_source_db

    db_name = "db_orphan_groups"
    write_source_db(db_name, "sqlite", parameters=True)

    activity_groups = {
        row.group
        for row in ActivityParameter.select(ActivityParameter.group).where(
            ActivityParameter.database == db_name
        )
    }
    assert activity_groups

    ActivityParameter.delete().where(ActivityParameter.database == db_name).execute()
    assert _broken_activity_parameter_groups()

    ParameterModify.fix_broken_groups()

    assert _broken_activity_parameter_groups() == []
    assert not {g.name for g in Group.select()} & activity_groups


def test_database_duplicate(monkeypatch, qtbot, basic_database):
    from activity_browser.app.actions.database.database_duplicate import NewDatabaseDialog, DuplicateDatabaseDialog
    from activity_browser.bwutils.commontasks import count_database_records

    dup_db = "db_that_is_duplicated"
    source_count = count_database_records(basic_database.name)

    monkeypatch.setattr(
        NewDatabaseDialog,
        "get_new_database_data",
        staticmethod(lambda *args, **kwargs: (dup_db, "functional_sqlite", True)),
    )

    assert dup_db not in bd.databases

    app.actions.DatabaseDuplicate.run(basic_database.name)

    dialog = app.main_window.findChild(DuplicateDatabaseDialog)
    with qtbot.waitSignal(dialog.dup_thread.finished, timeout=60 * 1000):
        pass

    assert basic_database.name in bd.databases
    assert dup_db in bd.databases
    assert count_database_records(dup_db) == source_count

    loader = app.metadata.loader
    for _ in range(200):
        if len(app.metadata.get_database_metadata(dup_db, ["name"])) == source_count:
            break
        if loader.secondary_status != "done":
            qtbot.wait(50)
            continue
        qtbot.wait(50)

    assert len(app.metadata.get_database_metadata(dup_db, ["name"])) == source_count


def test_database_export_excel(monkeypatch, qtbot, basic_database, tmp_path):
    """Test exporting a database to Excel format."""
    from activity_browser.app.actions.database.database_export_excel import ExportExcelSetup
    
    # Mock the file dialog to return a path
    test_path = str(tmp_path / "test_export.xlsx")
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (test_path, "")),
    )
    
    # Call the action
    app.actions.DatabaseExportExcel.run([basic_database.name])
    
    # Find the wizard dialog and wait for the export thread to finish
    wizard = app.main_window.findChild(ExportExcelSetup)
    assert wizard is not None
    
    # Wait for the export thread to finish
    export_page = wizard.currentPage()
    with qtbot.waitSignal(export_page.thread.finished, timeout=10 * 1000):
        pass
    
    # Close the wizard
    wizard.close()


def test_database_export_bw2package(monkeypatch, qtbot, basic_database, tmp_path):
    """Test exporting a database to BW2Package format."""
    from activity_browser.app.actions.database.database_export_bw2package import ExportBW2PackageSetup
    
    # Mock the file dialog to return a path
    test_path = str(tmp_path / "test_export.bw2package")
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (test_path, "")),
    )
    
    # Call the action
    app.actions.DatabaseExportBW2Package.run([basic_database.name])
    
    # Find the wizard dialog and wait for the export thread to finish
    wizard = app.main_window.findChild(ExportBW2PackageSetup)
    assert wizard is not None
    
    # Wait for the export thread to finish
    export_page = wizard.currentPage()
    with qtbot.waitSignal(export_page.thread.finished, timeout=10 * 1000):
        pass
    
    # Close the wizard
    wizard.close()


def test_database_new(monkeypatch, basic_database):
    from activity_browser.app.actions.database.database_new import NewDatabaseDialog

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

    app.actions.DatabaseNew.run()

    assert new_db in bd.databases

    db_number = len(bd.databases)

    app.actions.DatabaseNew.run()

    assert db_number == len(bd.databases)


def test_database_delete_multiple(monkeypatch, basic_database):
    """Test that multiple databases can be deleted at once."""
    from activity_browser.app.actions.database.database_new import NewDatabaseDialog

    # Create two additional databases
    db2 = "test_db_2"
    db3 = "test_db_3"

    for db_name in [db2, db3]:
        monkeypatch.setattr(
            NewDatabaseDialog,
            "get_new_database_data",
            staticmethod(lambda *args, db=db_name, **kwargs: (db, "functional_sqlite", True)),
        )
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
        )
        app.actions.DatabaseNew.run()

    assert db2 in bd.databases
    assert db3 in bd.databases

    # Mock the confirmation dialog
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    # Delete both databases at once
    app.actions.DatabaseDelete.run([db2, db3])

    assert db2 not in bd.databases
    assert db3 not in bd.databases
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
#     app.actions.DatabaseRelink.run(db)
#
#     assert db in databases
#     assert from_db in databases
#     assert to_db in databases
#     assert from_db not in Database(db).find_dependents()
#     assert to_db in Database(db).find_dependents()

