# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from random import randint
import os


def create_path(folder, filename):
    return os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'icons',
        folder,
        filename
    )


class Icons(object):
    # free icons from http://www.flaticon.com/search/history
    to_multi_lca = create_path('context', 'add.png')
    to_edited_activity = create_path('context', 'to_edited_activity.png')
    delete = create_path('context', 'delete.png')

    new = create_path('metaprocess', 'new_metaprocess.png')
    save_mp = create_path('metaprocess', 'save_metaprocess.png')
    load_db = create_path('metaprocess', 'open_database.png')
    add_db = create_path('metaprocess', 'add_database.png')
    save_db = create_path('metaprocess', 'save_database.png')
    close_db = create_path('metaprocess', 'close_database.png')
    graph_mp = create_path('metaprocess', 'graph_metaprocess.png')
    graph_lmp = create_path('metaprocess', 'graph_linkedmetaprocess.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')
    cut = create_path('metaprocess', 'cut.png')
    duplicate = create_path('metaprocess', 'duplicate.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')

    search = create_path('main', 'search.png')
    key = create_path('main', 'key.png')

    @property
    def pony(self):
        return create_path('pony', 'pony%s.png' % randint(1, 7))


icons = Icons()
