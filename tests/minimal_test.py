import os
import sys

from pytestqt import qtbot

p = os.path.abspath(os.path.join(os.path.split(__file__)[0], '..'))
print(p)
sys.path.append(p)

from lca_activity_browser.app import Application


def test_minimal(qtbot):
    app = Application()
    qtbot.addWidget(app)
