# -*- coding: utf-8 -*-
"""Shared run-action button chrome (Create / Write)."""
from __future__ import annotations

from qtpy import QtWidgets

RUN_BUTTON_STYLE = "background-color: #57965C;"


def style_run_button(button: QtWidgets.QPushButton) -> None:
    """Match calculation-setup Calculate: green fill + forward icon."""
    button.setStyleSheet(RUN_BUTTON_STYLE)
    try:
        from activity_browser.ui.icons import qicons

        button.setIcon(qicons.forward)
    except ImportError:
        pass
