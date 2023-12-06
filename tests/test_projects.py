# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtCore, QtWidgets
from activity_browser.ui.widgets.dialog import ProjectDeletionDialog
from activity_browser.signals import signals
from activity_browser.settings import ab_settings
from activity_browser.controllers import ProjectController
import os


def test_new_project(qtbot, ab_app, monkeypatch):
    """Test creating a new project."""
    qtbot.waitExposed(ab_app.main_window)
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText",
        staticmethod(lambda *args, **kwargs: ("pytest_project_del", True))
    )
    project_tab = ab_app.main_window.left_panel.tabs['Project']

    with qtbot.waitSignal(signals.projects_changed, timeout=2*1000):  # 2 seconds
        qtbot.mouseClick(
            project_tab.projects_widget.new_project_button,
            QtCore.Qt.LeftButton
        )
    assert bw.projects.current == 'pytest_project_del'


def test_change_project(qtbot, ab_app):
    """Test switching between projects."""
    qtbot.waitExposed(ab_app.main_window)
    assert bw.projects.current == 'pytest_project_del'
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    combobox = project_tab.projects_widget.projects_list
    assert 'default' in bw.projects
    assert 'default' in combobox.project_names

    with qtbot.waitSignal(signals.change_project, timeout=2*1000):  # 2 seconds
        combobox.activated.emit(combobox.project_names.index('default'))
    assert bw.projects.current == 'default'

    with qtbot.waitSignal(signals.change_project, timeout=2*1000):  # 2 seconds
        combobox.activated.emit(combobox.project_names.index('pytest_project_del'))
    assert bw.projects.current == 'pytest_project_del'


def test_delete_project(qtbot, ab_app, monkeypatch):
    """Test deleting a project."""
    qtbot.waitExposed(ab_app.main_window)
    assert bw.projects.current == 'pytest_project_del'

    # patch the confirmation dialog to confirm
    monkeypatch.setattr(ProjectDeletionDialog, 'exec_', lambda self: ProjectDeletionDialog.Accepted)

    # patch the info dialog where user is informed of successful delete
    monkeypatch.setattr(
               QtWidgets.QMessageBox, "information",
               staticmethod(lambda *args: QtWidgets.QMessageBox.Yes)
           )

    project_tab = ab_app.main_window.left_panel.tabs['Project']

    with qtbot.waitSignal(signals.projects_changed, timeout=2*1000):  # 2 seconds
        qtbot.mouseClick(
            project_tab.projects_widget.delete_project_button,
            QtCore.Qt.LeftButton
        )
    assert bw.projects.current == ab_settings.startup_project

def test_export_import_projects(qtbot, ab_app, monkeypatch):
    """Test exporting and importing of a project."""
    qtbot.waitExposed(ab_app.main_window)
    used_project = 'default'
    assert bw.projects.current == used_project

    menu_bar = ab_app.main_window.menu_bar

    # create a folder to use for export/import
    target_dir = os.path.join(os.getcwd(), 'export_import')
    os.mkdir(target_dir)

    # EXPORT
    # patch the export button to run ProjectController.export_project()
    monkeypatch.setattr(
        ProjectController, "export_project", lambda *args: None
    )
    # patch the file_dialog to return target_dir
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getExistingDirectory",
        staticmethod(lambda *args, **kwargs: (target_dir, True))
    )

    # start the export
    with qtbot.waitSignal(signals.export_database, timeout=5*60*1000):  # 5 minutes
        menu_bar.export_proj_action.trigger()

    # get all the files that match the export name structure in the target folder
    files = [f for f in os.listdir(target_dir) if f.startswith(f'brightway2-project-{used_project}') and f.endswith('tar.gz')]

    # there should only exist 1 exported file in the folder
    assert len(files) == 1

    # IMPORT



