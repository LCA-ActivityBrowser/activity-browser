import brightway2 as bw
from PySide2 import QtCore, QtWidgets

def test_new_calculation_setup(qtbot, ab_app, monkeypatch):
    assert bw.projects.current == 'pytest_project'

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('pytest_cs', True))
    )

    cs_tab = ab_app.main_window.right_panel.tabs["LCA Setup"]
    qtbot.mouseClick(
        cs_tab.new_cs_button,
        QtCore.Qt.LeftButton
    )

    assert len(bw.calculation_setups) == 1
    assert "pytest_cs" in bw.calculation_setups

def test_delete_calculation_setup(qtbot, ab_app, monkeypatch):
    assert bw.projects.current == 'pytest_project'
    assert len(bw.calculation_setups) == 1

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'warning',
        lambda *args, **kwargs: QtWidgets.QMessageBox.Yes
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'information',
        lambda *args, **kwargs: True
    )

    cs_tab = ab_app.main_window.right_panel.tabs["LCA Setup"]

    assert cs_tab.list_widget.name == 'pytest_cs'

    qtbot.mouseClick(
        cs_tab.delete_cs_button,
        QtCore.Qt.LeftButton
    )


    assert len(bw.calculation_setups) == 0
    assert "pytest_cs" not in bw.calculation_setups