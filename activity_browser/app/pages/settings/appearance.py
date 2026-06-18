# -*- coding: utf-8 -*-
from qtpy import QtWidgets

from activity_browser.app import settings
from activity_browser.app.pages.settings.base import BaseSettingsChapter
from activity_browser.ui.widgets.plot import DEFAULT_PLOT_PALETTE, PLOT_PALETTES


def _labeled_group(title: str, rows: list[tuple[str, QtWidgets.QWidget]]) -> QtWidgets.QGroupBox:
    group = QtWidgets.QGroupBox(title)
    grid = QtWidgets.QGridLayout()
    for i, (label, widget) in enumerate(rows):
        grid.addWidget(QtWidgets.QLabel(label), i, 0)
        grid.addWidget(widget, i, 1)
    group.setLayout(grid)
    return group


class AppearanceSettingsChapter(BaseSettingsChapter):
    """Chapter for appearance-related settings."""

    theme_map = {
        "default": "System default",
        "light": "Light theme",
        "dark": "Dark theme",
    }
    pane_tab_position_map = {
        "top": "Top",
        "bottom": "Bottom",
        "left": "Left",
        "right": "Right",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_combo = QtWidgets.QComboBox()
        self.palette_combo = QtWidgets.QComboBox()
        self.pane_tab_position_combo = QtWidgets.QComboBox()
        self.database_products_as_cards = QtWidgets.QCheckBox("Show database contents as cards")
        self.database_products_as_cards.setToolTip(
            "When enabled, the database process list uses a card layout instead of a detailed table."
        )
        self.build_layout()
        self.connect_signals()
        self.reset()

    def connect_signals(self):
        for widget in (
            self.theme_combo,
            self.palette_combo,
            self.pane_tab_position_combo,
        ):
            widget.currentTextChanged.connect(lambda: self.changed.emit())
        self.database_products_as_cards.checkStateChanged.connect(lambda _: self.changed.emit())

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(_labeled_group("Theme", [("Theme:", self.theme_combo)]))
        layout.addWidget(_labeled_group("Plots", [("Palette:", self.palette_combo)]))
        layout.addWidget(
            _labeled_group("Pane Tab Position", [("Position:", self.pane_tab_position_combo)])
        )
        database_group = QtWidgets.QGroupBox("Database pane")
        db_layout = QtWidgets.QVBoxLayout()
        db_layout.addWidget(self.database_products_as_cards)
        database_group.setLayout(db_layout)
        layout.addWidget(database_group)
        layout.addStretch()
        self.setLayout(layout)

    @staticmethod
    def _saved_palette() -> str:
        name = settings["appearance"].get("plot_palette", DEFAULT_PLOT_PALETTE)
        return name if name in PLOT_PALETTES else DEFAULT_PLOT_PALETTE

    def reset(self):
        appearance = settings["appearance"]
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_map.values())
        self.theme_combo.setCurrentText(self.theme_map.get(appearance["theme"], "System default"))
        self.palette_combo.clear()
        self.palette_combo.addItems(PLOT_PALETTES)
        self.palette_combo.setCurrentText(self._saved_palette())
        self.pane_tab_position_combo.clear()
        self.pane_tab_position_combo.addItems(self.pane_tab_position_map.values())
        self.pane_tab_position_combo.setCurrentText(
            self.pane_tab_position_map.get(appearance["pane_tab_position"], "Bottom")
        )
        self.database_products_as_cards.setChecked(bool(appearance.get("database_products_as_cards", False)))

    def has_changes(self):
        appearance = settings["appearance"]
        return {
            "theme": self.theme_combo.currentText(),
            "plot_palette": self.palette_combo.currentText(),
            "pane_tab_position": self.pane_tab_position_combo.currentText(),
            "database_products_as_cards": self.database_products_as_cards.isChecked(),
        } != {
            "theme": self.theme_map.get(appearance["theme"], "System default"),
            "plot_palette": self._saved_palette(),
            "pane_tab_position": self.pane_tab_position_map.get(
                appearance["pane_tab_position"], "Bottom"
            ),
            "database_products_as_cards": bool(appearance.get("database_products_as_cards", False)),
        }

    def set_settings(self):
        appearance = settings["appearance"]
        appearance["theme"] = next(
            k for k, v in self.theme_map.items() if v == self.theme_combo.currentText()
        )
        appearance["plot_palette"] = self.palette_combo.currentText()
        appearance["pane_tab_position"] = next(
            k
            for k, v in self.pane_tab_position_map.items()
            if v == self.pane_tab_position_combo.currentText()
        )
        appearance["database_products_as_cards"] = self.database_products_as_cards.isChecked()
