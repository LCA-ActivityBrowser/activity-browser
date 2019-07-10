# -*- coding: utf-8 -*-
from itertools import zip_longest

from PyQt5.QtWidgets import (QBoxLayout, QComboBox, QHBoxLayout, QRadioButton,
                             QVBoxLayout, QWidget)

from ..style import header, horizontal_line


def add_objects_to_layout(layout: QBoxLayout, *objects) -> QBoxLayout:
    """ For each given object, attempt to add it to the given layout in order.
    """
    for item in objects:
        if isinstance(item, QBoxLayout):
            layout.addLayout(item)
        elif isinstance(item, QWidget):
            layout.addWidget(item)
    return layout


def build_radiobutton(name: str, state: bool=False) -> QRadioButton:
    button = QRadioButton(name)
    button.setChecked(state)
    return button


def build_combobox(scroll: bool=False) -> QComboBox:
    box = QComboBox()
    box.scroll = scroll
    return box


def get_header_layout(header_text: str) -> QVBoxLayout:
    vlayout = QVBoxLayout()
    vlayout.addWidget(header(header_text))
    vlayout.addWidget(horizontal_line())
    return vlayout


def get_radio_buttons(names: list, states: list=[]) -> (list, QHBoxLayout):
    """ Generate radiobuttons from a list of names and states.

    Returns the buttons and an HBox layout in which the buttons are placed
    """
    assert len(names) >= len(states), "Cannot have more states than names"

    buttons = [
        build_radiobutton(n, s) for n, s in
            zip_longest(names, states, fillvalue=True)
    ]

    box_layout = QHBoxLayout()
    add_objects_to_layout(box_layout, *buttons)
    box_layout.addStretch(1)
    return buttons, box_layout
