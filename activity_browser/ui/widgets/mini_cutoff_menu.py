# -*- coding: utf-8 -*-
"""Classes related to the cutoff options menu in contributions tabs.

These classes contain all menu items required to modify the cutoffs of the MLCA results. The
CutoffMenu class is responsible for assembling the menu. Each different menu item is contained in
its separate class.
"""

from collections import namedtuple
from typing import Union

import numpy as np
from PySide2 import QtCore
from PySide2.QtCore import QLocale, Qt, Signal, Slot
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QSlider, QLabel,
    QLineEdit, QPushButton, QButtonGroup
)

from PySide2.QtGui import QIntValidator, QDoubleValidator

from ..style import vertical_line, horizontal_line

# These tuples are used in referring to the two Types and three Labels used
Types = namedtuple("types", ("relative", "topx"))


class MiniCutoffMenu(QWidget):
    """This class assembles the cutoff menu from the other classes in this module."""

    slider_change = Signal()

    def __init__(self, parent=None, cutoff_value=0.01, limit_type="percent"):
        super().__init__(parent)
        self.cutoff_value = cutoff_value
        self.limit_type = limit_type

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        self.validators = Types(
            QDoubleValidator(0.001, 100.0, 1, self), QIntValidator(0, 50, self)
        )
        self.validators.relative.setLocale(locale)
        self.validators.topx.setLocale(locale)
        self.buttons = Types(QRadioButton("Relative"), QRadioButton("Top #"))
        self.buttons.relative.setChecked(True)
        self.buttons.relative.setToolTip(
            "This cut-off type shows the selected top percentage of contributions (for example the \
top 10% contributors)")
        self.buttons.topx.setToolTip(
            "This cut-off type shows the selected top number of contributions (for example the top \
5 contributors)")
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.buttons.relative, 0)
        self.button_group.addButton(self.buttons.topx, 1)
        self.units = Types("% of total", "top #")
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_slider_line.setToolTip("This box can set a precise cut-off value for the \
contributions to be shown")
        self.cutoff_slider_line.setLocale(locale)
        self.unit_label = QLabel()

        self.unit_label.setText(self.units.relative)
        self.cutoff_slider_line.setText(str(self.cutoff_value * 100))
        self.cutoff_slider_line.setValidator(self.validators.relative)

        self.debounce_text = QtCore.QTimer()
        self.debounce_text.setInterval(750)
        self.debounce_text.setSingleShot(True)

        self.make_layout()
        self.connect_signals()

    def connect_signals(self):
        """Connect the signals of the menu."""
        # Cut-off types
        self.buttons.relative.toggled.connect(self.cutoff_type_check)
        self.debounce_text.timeout.connect(self.initiate_text_change)
        self.cutoff_slider_line.textChanged.connect(self.debounce_text.start)


    def initiate_text_change(self):
        result = self.cutoff_slider_line.validator().validate(self.cutoff_slider_line.text(), 0)
        if result is QDoubleValidator.Invalid or result is QDoubleValidator.Intermediate:
            return
        if self.is_relative:
            self.cutoff_slider_relative_check()
        else:
            self.cutoff_slider_topx_check()


    @property
    def is_relative(self) -> bool:
        """Check if relative button is checked."""
        return self.buttons.relative.isChecked()


    @Slot(bool, name="isRelativeToggled")
    def cutoff_type_check(self, toggled: bool) -> None:
        """Dependent on cutoff-type, set the right labels.

        Slot connected to the relative radiobutton, the state of that button determines:
        - which sliders are visible
        - the unit shown
        - minimum and maximum
        - limit_type
        """
        self.cutoff_slider_line.blockSignals(True)
        self.cutoff_slider_line.clear()
        if toggled:
            self.unit_label.setText(self.units.relative)
            self.limit_type = "percent"
            self.cutoff_slider_line.setValidator(self.validators.relative)
        else:
            self.unit_label.setText(self.units.topx)
            self.limit_type = "number"
            self.cutoff_slider_line.setValidator(self.validators.topx)
        self.cutoff_slider_line.blockSignals(False)

    @Slot(str, name="sliderRelativeCheck")
    def cutoff_slider_relative_check(self):
        """If 'relative' selected, change the plots and tables to reflect the slider/line-edit."""
        self.cutoff_slider_line.blockSignals(True)
        cutoff = abs(float(self.cutoff_slider_line.text()))
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_value = (cutoff/100)
        self.slider_change.emit()

    @Slot(str, name="sliderTopXCheck")
    def cutoff_slider_topx_check(self):
        """If 'top #' selected, change the plots and tables to reflect the slider/line-edit."""
        self.cutoff_slider_line.blockSignals(True)
        cutoff = abs(int(self.cutoff_slider_line.text()))
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_value = int(cutoff)
        self.slider_change.emit()

    def make_layout(self):
        """Assemble the layout of the cutoff menu.

        Construct the layout for the cutoff menu widget. The initial layout is set to 'relative'.
        """
        layout = QHBoxLayout()

        # Cut-off types
        cutoff_type = QHBoxLayout()
        cutoff_type_label = QLabel("Cut-off type:")

        # Cut-off textbox
        cutoff_slider_ledit = QHBoxLayout()

        # Assemble types
        cutoff_type.addWidget(cutoff_type_label)
        cutoff_type.addWidget(self.buttons.relative)
        cutoff_type.addWidget(self.buttons.topx)

        cutoff_slider_ledit.addWidget(QLabel('Cut-off:'))
        cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
        cutoff_slider_ledit.addWidget(self.unit_label)
        cutoff_slider_ledit.addStretch(1)

        # Assemble cut-off menu
        layout.addLayout(cutoff_type)
        layout.addWidget(vertical_line())
        layout.addLayout(cutoff_slider_ledit)
        layout.addStretch()

        self.setLayout(layout)
