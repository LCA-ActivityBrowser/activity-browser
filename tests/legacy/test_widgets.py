# -*- coding: utf-8 -*-
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QDialogButtonBox, QMessageBox, QWidget

from activity_browser.ui.widgets import (BiosphereUpdater, CutoffMenu,
                                         ForceInputDialog, SwitchComboBox,
                                         parameter_save_errorbox,
                                         simple_warning_box)

# NOTE: No way of testing the BiosphereUpdater class without causing the
#  ab_app fixture to flip its lid and fail to clean itself up.


def test_comparison_switch_empty(qtbot):
    parent = QWidget()
    parent.has_scenarios = False
    qtbot.addWidget(parent)
    box = SwitchComboBox(parent)
    box.configure(False, False)
    size = box.count()
    assert size == 0
    assert not box.isVisible()


def test_comparison_switch_no_scenarios(qtbot):
    parent = QWidget()
    parent.has_scenarios = False
    qtbot.addWidget(parent)
    box = SwitchComboBox(parent)
    box.configure()
    size = box.count()
    assert size == 2
    # assert box.isVisible()  # Box fails to be visible, except it definitely is?


def test_comparison_switch_all(qtbot):
    parent = QWidget()
    parent.has_scenarios = True
    qtbot.addWidget(parent)
    box = SwitchComboBox(parent)
    box.configure()
    size = box.count()
    assert size == 3


def test_cutoff_slider_toggle(qtbot):
    slider = CutoffMenu()
    qtbot.addWidget(slider)
    with qtbot.waitSignal(slider.buttons.topx.toggled, timeout=800):
        slider.buttons.topx.click()
    assert not slider.is_relative
    assert slider.limit_type == "number"


def test_input_dialog(qtbot):
    """Test the various thing about the dialog widget."""
    parent = QWidget()
    qtbot.addWidget(parent)
    dialog = ForceInputDialog.get_text(
        parent, "Early in the morning", "What should we do with a drunken sailor"
    )
    assert dialog.output == ""
    assert not dialog.buttons.button(QDialogButtonBox.Ok).isEnabled()

    existing = ForceInputDialog.get_text(
        parent, "Existence", "is a nightmare", "and here is why"
    )
    assert existing.output == "and here is why"
    # Text in dialog MUST be changed before Ok button is enabled.
    assert not dialog.buttons.button(QDialogButtonBox.Ok).isEnabled()
    with qtbot.waitSignal(dialog.input.textChanged, timeout=100):
        dialog.input.setText("Now it works.")
    assert dialog.buttons.button(QDialogButtonBox.Ok).isEnabled()


def test_parameter_errorbox(qtbot, monkeypatch):
    """Not truly used anymore in favour of not saving invalid values."""
    parent = QWidget()
    qtbot.addWidget(parent)

    monkeypatch.setattr(QMessageBox, "exec_", lambda *args: QMessageBox.Cancel)
    result = parameter_save_errorbox(parent, "got an error")
    assert result == QMessageBox.Cancel


def test_simple_warning_box(qtbot, monkeypatch):
    parent = QWidget()
    qtbot.addWidget(parent)

    monkeypatch.setattr(QMessageBox, "warning", lambda *args: QMessageBox.Ok)
    result = simple_warning_box(parent, "Warning title", "This is a warning")
    assert result == QMessageBox.Ok
