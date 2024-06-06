# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard

#
#
# def test_open_db_wizard_button(qtbot, ab_app, monkeypatch):
#     """Show that the signals and slots works for importing."""
#     assert bw.projects.current == 'pytest_project'
#     qtbot.waitForWindowShown(ab_app.main_window)
#     project_tab = ab_app.main_window.left_panel.tabs['Project']
#
#     # Monkeypatch the 'import_database_wizard' method in the controller
#     monkeypatch.setattr(
#         DatabaseController, "import_database_wizard", lambda *args: None
#     )
#     with qtbot.waitSignal(signals.import_database, timeout=500):
#         qtbot.mouseClick(
#             project_tab.databases_widget.import_database_button,
#             QtCore.Qt.LeftButton
#         )


def test_open_db_wizard(ab_app, qtbot):
    """Open the wizard itself."""
    qtbot.waitForWindowShown(ab_app.main_window)
    wizard = DatabaseImportWizard(ab_app.main_window)
    qtbot.addWidget(wizard)
    wizard.show()

    qtbot.mouseClick(
        wizard.button(QtWidgets.QWizard.CancelButton),
        QtCore.Qt.LeftButton
    )
