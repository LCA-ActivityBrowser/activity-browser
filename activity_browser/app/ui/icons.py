# -*- coding: utf-8 -*-
import os

from PySide2.QtGui import QIcon

from activity_browser import PACKAGE_DIRECTORY


def create_path(folder: str, filename: str) -> str:
    """ Builds a path to the image file.
    """
    return os.path.join(PACKAGE_DIRECTORY, "icons", folder, filename)


class Icons(object):
    # Icons from href="https://www.flaticon.com/
    # By https://www.flaticon.com/authors/freepik,
    # https://www.flaticon.com/authors/rami-mcmin,
    # and others
    # And are licensed by CC BY 3.0
    delete = create_path('context', 'delete.png')
    copy = create_path('context', 'copy.png')
    add = create_path('context', 'add.png')
    # Icon made by 'Roundicons' from www.flaticon.com
    question = create_path('context', 'question.png')

    add_db = create_path('metaprocess', 'add_database.png')
    close_db = create_path('metaprocess', 'close_database.png')
    cut = create_path('metaprocess', 'cut.png')
    duplicate = create_path('metaprocess', 'duplicate.png')
    graph_lmp = create_path('metaprocess', 'graph_linkedmetaprocess.png')
    graph_mp = create_path('metaprocess', 'graph_metaprocess.png')
    load_db = create_path('metaprocess', 'open_database.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')
    new = create_path('metaprocess', 'new_metaprocess.png')
    save_db = create_path('metaprocess', 'save_database.png')
    save_mp = create_path('metaprocess', 'save_metaprocess.png')

    debug = create_path('main', 'debug.png')
    forward = create_path('main', 'forward.png')
    right = create_path('main', 'right.png')
    left = create_path('main', 'left.png')
    backward = create_path('main', 'backward.png')
    edit = create_path('main', 'edit.png')
    key = create_path('main', 'key.png')
    search = create_path('main', 'search.png')
    switch = create_path('main', 'switch-state.png')
    ab = create_path('main', 'activitybrowser.png')
    graph_explorer = create_path('main', 'graph_explorer.png')
    calculate = create_path('main', 'calculate.png')


class QIcons(Icons):
    """ Using the Icons class, returns the same attributes, but as QIcon type
    """
    def __getattribute__(self, item):
        return QIcon(Icons.__getattribute__(self, item))


icons = Icons()
qicons = QIcons()
