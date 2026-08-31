# -*- coding: utf-8 -*-
"""Collapsible Configure form section with summary and status."""
from __future__ import annotations

from qtpy import QtCore, QtWidgets

_STATUS_COLORS = {
    "ok": "#2e7d32",
    "warn": "#ed6c02",
    "error": "#d32f2f",
    "neutral": "#616161",
}


class ConfigureSection(QtWidgets.QWidget):
    """Expandable section header plus content area."""

    def __init__(
        self,
        title: str,
        content: QtWidgets.QWidget,
        *,
        expanded: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.toggle_btn = QtWidgets.QToolButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
        )
        self.toggle_btn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toggle_btn.clicked.connect(self._on_toggled)
        header_layout.addWidget(self.toggle_btn)

        self.title_label = QtWidgets.QLabel(title)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        header_layout.addWidget(self.title_label)

        self.summary_label = QtWidgets.QLabel()
        self.summary_label.setWordWrap(True)
        header_layout.addWidget(self.summary_label, 1)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        header_layout.addWidget(self.status_label)

        layout.addWidget(header)

        self.content = content
        self.content.setVisible(expanded)
        layout.addWidget(self.content)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_btn.setChecked(expanded)
        self._on_toggled()

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def set_status(self, text: str, *, level: str = "neutral") -> None:
        self.status_label.setText(text)
        color = _STATUS_COLORS.get(level, _STATUS_COLORS["neutral"])
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _on_toggled(self) -> None:
        expanded = self.toggle_btn.isChecked()
        self.content.setVisible(expanded)
        self.toggle_btn.setArrowType(
            QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
        )
