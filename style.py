#!/usr/bin/env python
# -*- coding: utf-8 -*-


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


class IconsContextMenu():
    to_multi_lca = 'icons/context/add.png'
    to_edited_activity = 'icons/context/to_edited_activity.png'
    delete = 'icons/context/delete.png'

class IconsMetaProcess():
    new = 'icons/metaprocess/new_metaprocess.png'
    save_mp = 'icons/metaprocess/save_metaprocess.png'
    load_db = 'icons/metaprocess/open_database.png'
    add_db = 'icons/metaprocess/add_database.png'
    save_db = 'icons/metaprocess/save_database.png'
    close_db = 'icons/metaprocess/close_database.png'
    graph_mp = 'icons/metaprocess/graph_metaprocess.png'
    graph_lmp = 'icons/metaprocess/graph_linkedmetaprocess.png'

    # Context Menus
    metaprocess = 'icons/metaprocess/metaprocess.png'
    cut = 'icons/metaprocess/cut.png'
    duplicate = 'icons/metaprocess/duplicate.png'

class MyIcons():
    context = IconsContextMenu()
    mp = IconsMetaProcess()

icons = MyIcons()