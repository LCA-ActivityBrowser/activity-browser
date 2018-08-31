# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtWidgets


bold_font = QtGui.QFont()
bold_font.setBold(True)
bold_font.setPointSize(12)

def horizontal_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def header(label):
    label = QtWidgets.QLabel(label)
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


class TableItemStyle:
    COLOR_CODE = {
        'default': (0, 0, 0),  # black
        'product': (0, 132, 130),
        'reference product': (0, 132, 130),
        'name': (0, 2, 140),
        'activity': (0, 72, 216),
        'amount': (0, 0, 0),
        # 'unit': (51, 153, 255),
        'unit': (0, 0, 0),
        'location': (72, 0, 140),
        'database': (96, 96, 96),
        'categories': (0, 0, 0),
        'key': (0, 0, 0),
    }

    def __init__(self):
        self.brushes = {}
        for key, values in self.COLOR_CODE.items():
            self.brushes.update({
                key: QtGui.QBrush(QtGui.QColor(*values))
            })


style_table = TableStyle()
style_item = TableItemStyle()


# self.setAutoFillBackground(True)
# p = self.palette()
# p.setColor(self.backgroundRole(), QtCore.Qt.gray)
# self.setPalette(p)


# class IconsContextMenu():
#     to_multi_lca = 'icons/context/add.png'
#     to_edited_activity = 'icons/context/to_edited_activity.png'
#     delete = 'icons/context/delete.png'
#
# class IconsMetaProcess():
#     new = 'icons/metaprocess/new_metaprocess.png'
#     save_mp = 'icons/metaprocess/save_metaprocess.png'
#     load_db = 'icons/metaprocess/open_database.png'
#     add_db = 'icons/metaprocess/add_database.png'
#     save_db = 'icons/metaprocess/save_database.png'
#     close_db = 'icons/metaprocess/close_database.png'
#     graph_mp = 'icons/metaprocess/graph_metaprocess.png'
#     graph_lmp = 'icons/metaprocess/graph_linkedmetaprocess.png'
#
#     # Context Menus
#     metaprocess = 'icons/metaprocess/metaprocess.png'
#     cut = 'icons/metaprocess/cut.png'
#     duplicate = 'icons/metaprocess/duplicate.png'
#
# class MyIcons():
#     context = IconsContextMenu()
#     mp = IconsMetaProcess()
#
# icons = MyIcons()