# -*- coding: utf-8 -*-
import os

# type "localhost:3999" in Chrome for DevTools of AB web content
from activity_browser.bwutils.filesystem import get_package_path

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "3999"


def get_static_js_path(file_name: str = "") -> str:
    return str(get_package_path() / "static" / "javascript" / file_name)


def get_static_css_path(file_name: str = "") -> str:
    return str(get_package_path() / "static" / "css" / file_name)