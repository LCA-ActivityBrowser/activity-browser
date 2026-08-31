# -*- coding: utf-8 -*-
"""Shared run-action button chrome (Create / Write)."""
from __future__ import annotations

from qtpy import QtWidgets

RUN_BUTTON_STYLE = "background-color: #57965C;"


def style_run_button(button: QtWidgets.QPushButton) -> None:
    """Green fill for Create / Write run actions (no host icon dependency)."""
    button.setStyleSheet(RUN_BUTTON_STYLE)
