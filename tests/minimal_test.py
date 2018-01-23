# -*- coding: utf-8 -*-
from activity_browser import Application


def test_minimal(qtbot):
    app = Application()
    qtbot.addWidget(app)
