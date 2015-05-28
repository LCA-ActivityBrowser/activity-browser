# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *


from random import randint
import os

# COLORS
# table current activity (RGB)
colors_table_current_activity = {
    'product': (0, 0, 204),
    'name': (0, 0, 0),
    'amount': (0, 0, 0),
    'unit': (51, 153, 255),
    # 'unit': (0, 76, 153),
    # 'unit': (0, 102, 204),
    'location': (0, 102, 51),
    'database': (96, 96, 96),
}

# STYLESHEETS
stylesheet_current_activity = """
QTableWidget {
    border-radius: 5px;
    background-color: rgb(224, 224, 224);
    border:1px solid rgb(96, 96, 96);
    margin:0px;
    }
"""

def _(path):
    return os.path.join(os.path.dirname(__file__), path)


class IconsContextMenu(object):
    to_multi_lca = _('icons/context/add.png')
    to_edited_activity = _('icons/context/to_edited_activity.png')
    delete = _('icons/context/delete.png')


class IconsMetaProcess(object):
    new = _('icons/metaprocess/new_metaprocess.png')
    save_mp = _('icons/metaprocess/save_metaprocess.png')
    load_db = _('icons/metaprocess/open_database.png')
    add_db = _('icons/metaprocess/add_database.png')
    save_db = _('icons/metaprocess/save_database.png')
    close_db = _('icons/metaprocess/close_database.png')
    graph_mp = _('icons/metaprocess/graph_metaprocess.png')
    graph_lmp = _('icons/metaprocess/graph_linkedmetaprocess.png')

    # Context Menus
    metaprocess = _('icons/metaprocess/metaprocess.png')
    cut = _('icons/metaprocess/cut.png')
    duplicate = _('icons/metaprocess/duplicate.png')


class MyIcons(object):
    context = IconsContextMenu()
    mp = IconsMetaProcess()
    metaprocess = _('icons/metaprocess/metaprocess.png')

    def main(self):
        return _('icons/pony/pony%s.png' % randint(1, 7))

icons = MyIcons()
