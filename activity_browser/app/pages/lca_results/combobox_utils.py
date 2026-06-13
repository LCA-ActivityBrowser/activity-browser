"""Shared QComboBox helpers for LCA Results tabs and graph navigators."""

from __future__ import annotations

from typing import Sequence

from qtpy import QtCore, QtWidgets


def set_combobox_index(box: QtWidgets.QComboBox, index: int) -> None:
    """Set the current index without emitting signals."""
    box.blockSignals(True)
    box.setCurrentIndex(index)
    box.blockSignals(False)


def update_combobox(
    box: QtWidgets.QComboBox,
    labels: Sequence[str],
    *,
    preserve_selection: bool = True,
) -> None:
    """Replace combo items, optionally keeping the current label when still valid."""
    current = box.currentText() if preserve_selection else ""
    box.blockSignals(True)
    box.clear()
    if labels:
        box.insertItems(0, list(labels))
        if current and current in labels:
            box.setCurrentIndex(labels.index(current))
    box.blockSignals(False)


def scenario_labels(parent) -> list[str]:
    """Scenario names from the parent LCA results page, if any."""
    mlca = getattr(parent, "mlca", None)
    if mlca is None or not getattr(parent, "has_scenarios", False):
        return []
    return list(getattr(mlca, "scenario_names", []) or [])


def configure_scenario_widgets(
    *,
    has_scenarios: bool,
    scenario_box: QtWidgets.QComboBox,
    scenario_label: QtWidgets.QLabel,
    parent,
) -> list[str]:
    """Show/hide scenario controls and refresh the scenario combo."""
    scenario_box.setVisible(has_scenarios)
    scenario_label.setVisible(has_scenarios)
    labels = scenario_labels(parent) if has_scenarios else []
    if has_scenarios:
        update_combobox(scenario_box, labels)
    return labels
