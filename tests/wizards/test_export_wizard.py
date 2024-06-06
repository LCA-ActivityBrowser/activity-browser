from PySide2 import QtCore, QtWidgets

from activity_browser.ui.wizards.db_export_wizard import DatabaseExportWizard

# TODO: Add fixture with small database to export.


# def test_trigger_export_wizard(qtbot, ab_app, monkeypatch):
#     """Test the triggers for the export wizard."""
#     assert bw.projects.current == 'pytest_project'
#     qtbot.waitForWindowShown(ab_app.main_window)
#
#     menu_bar = ab_app.main_window.menu_bar
#
#     monkeypatch.setattr(
#         DatabaseController, "export_database_wizard", lambda *args: None
#     )
#     # Trigger the action for export database.
#     with qtbot.waitSignal(signals.export_database, timeout=500):
#         menu_bar.export_db_action.trigger()


def test_open_export_wizard(ab_app, qtbot):
    """Actually open the export wizard."""
    qtbot.waitForWindowShown(ab_app.main_window)
    wizard = DatabaseExportWizard(ab_app.main_window)
    qtbot.addWidget(wizard)
    wizard.show()

    # The initial field for the database does not allow 'finish'
    assert wizard.field("database_choice") == "-----"
    assert not wizard.button(DatabaseExportWizard.FinishButton).isEnabled()

    # And close it down
    qtbot.mouseClick(
        wizard.button(QtWidgets.QWizard.CancelButton),
        QtCore.Qt.LeftButton
    )
