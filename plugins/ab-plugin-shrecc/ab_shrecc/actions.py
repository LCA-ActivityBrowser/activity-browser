# -*- coding: utf-8 -*-
"""Open SHRECC plugin page from Plugins menu."""
from activity_browser.plugins import ABAction, reveal_page

from . import ids


class OpenShreccPage(ABAction):
    text = "Open SHRECC"

    @staticmethod
    def run():
        reveal_page(ids.PAGE)
