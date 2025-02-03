# -*- coding: utf-8 -*-
from qtpy import QtGui, QtWidgets
from activity_browser import ab_settings

default_font = QtGui.QFont("Arial", 8)

bold_font = QtGui.QFont()
bold_font.setBold(True)
bold_font.setPointSize(12)


def horizontal_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def vertical_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.VLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def header(text):
    label = QtWidgets.QLabel(text)
    label.setFont(bold_font)
    return label


# COLORS values are RGB


class TableStyle:
    # STYLESHEETS
    stylesheet_current_activity = """
        QTableWidget {
            border-radius: 5px;
            background-color: rgb(224, 224, 224);
            border:1px solid rgb(96, 96, 96);
            margin:0px;
            }
        """
    # does not need to have widths for all columns, but starts at col 0
    custom_column_widths = {
        # "ActivitiesTable": [200, 250, 50],
    }


class ActivitiesTab:
    style_sheet_read_only = """
        QToolBar {
            spacing: 8px;
        }
        QTabWidget::pane {
            border-top: 0px solid rgb(128,0,0); /*red line (read-only indicator) - removed due to request */
            /*border-bottom: 3px solid rgb(128,0,0);*/
        }
    """
    style_sheet_editable = """
        QToolBar {
            spacing: 8px;
        }
        QTabWidget::pane {
            border-top: 3px solid rgb(0,128,0);
            /* border-bottom: 3px solid rgb(0,128,0);*/
        }
        """


class ActivitiesPanel:
    style_sheet = """
    """


class TableItemStyle:
    if ab_settings.theme == "Dark theme compatibility":
        COLOR_CODE = {
            "default": (255, 255, 255),  # white
            "name": (85, 170, 255),
            "activity": (85, 170, 255),
            "location": (255, 85, 255),
            "database": (200, 200, 200),
            "key": (200, 200, 200),
            "modified": (0, 120, 200),
            "duplicate": (200, 0, 0),
            "deleted": (100, 100, 100),
            "new": (0, 200, 0),
            # Colorblind friendly colors based on the Wong palette from https://davidmathlogic.com/colorblind:
            # https://davidmathlogic.com/colorblind/#%23000000-%23C7C7C7-%23009E73-%23EBC120-%23D55E00
            "good": (0, 158, 115),
            "missing": (85, 85, 85),
            "warning": (235, 193, 32),
            "critical": (213, 94, 0),
            "hyperlink": (0, 100, 238),
        }
    else:  # light theme default
        COLOR_CODE = {
            "default": (0, 0, 0),  # black
            # 'product': (0, 132, 130),
            "product": (0, 0, 0),
            # 'reference product': (0, 132, 130),
            "reference product": (0, 0, 0),
            "name": (0, 2, 140),
            "activity": (0, 72, 216),
            "amount": (0, 0, 0),
            # 'unit': (51, 153, 255),
            "unit": (0, 0, 0),
            "location": (72, 0, 140),
            "database": (96, 96, 96),
            "categories": (0, 0, 0),
            "key": (96, 96, 96),
            "modified": (0, 0, 200),
            "duplicate": (200, 0, 0),
            "deleted": (180, 180, 180),
            "new": (0, 200, 0),
            # Colorblind friendly colors based on the Wong palette from https://davidmathlogic.com/colorblind:
            # https://davidmathlogic.com/colorblind/#%23000000-%23C7C7C7-%23009E73-%23EBC120-%23D55E00
            "good": (0, 158, 115),
            "missing": (199, 199, 199),
            "warning": (235, 193, 32),
            "critical": (213, 94, 0),
            "hyperlink": (0, 0, 238),
        }

    def __init__(self):
        self.brushes: dict[str, QtGui.QBrush] = {}
        for key, values in self.COLOR_CODE.items():
            self.brushes.update({key: QtGui.QBrush(QtGui.QColor(*values))})


class GroupBoxStyle:
    __slots__ = []
    border_title = """
    QGroupBox {
        border: 1px solid gray; border-radius: 5px; margin-top: 7px; margin-bottom: 7px; padding: 0px
    }
    QGroupBox::title {top:-7 ex;left: 10px; subcontrol-origin: border}
    """


style_activity_panel = ActivitiesPanel
style_activity_tab = ActivitiesTab
style_table = TableStyle()
style_item = TableItemStyle()
style_group_box = GroupBoxStyle
