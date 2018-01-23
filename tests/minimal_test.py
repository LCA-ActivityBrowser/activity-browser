# import os
# import sys

from pytestqt import qtbot

# p = os.path.abspath(os.path.join(os.path.split(__file__)[0], '..'))
# sys.path.append(p)

from activity_browser import Application


def test_minimal(qtbot):
    app = Application()
    qtbot.addWidget(app)
