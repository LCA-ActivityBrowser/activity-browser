# -*- coding: utf-8 -*-
"""Example plugin menu actions."""
from activity_browser.plugins import ABAction, reveal_page, reveal_pane

from . import ids


class ShowExamplePage(ABAction):
    text = "Show example page"

    @staticmethod
    def run():
        reveal_page(ids.PAGE)


class ShowExamplePane(ABAction):
    text = "Show example pane"

    @staticmethod
    def run():
        reveal_pane(ids.PANE)
