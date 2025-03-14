# -*- coding: utf-8 -*-
import os

# type "localhost:3999" in Chrome for DevTools of AB web content
from activity_browser.utils import get_base_path

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "3999"


def get_static_js_path(file_name: str = "") -> str:
    return str(get_base_path().joinpath("static", "javascript", file_name))


def get_static_css_path(file_name: str = "") -> str:
    return str(get_base_path().joinpath("static", "css", file_name))
