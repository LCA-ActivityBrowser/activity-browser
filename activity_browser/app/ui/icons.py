# -*- coding: utf-8 -*-
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
    # Icons from href="http://www.flaticon.com/
    # By http://www.flaticon.com/authors/freepik,
    # http://www.flaticon.com/authors/rami-mcmin,
    # and others
    # And are licensed by CC BY 3.0
    delete = create_path('context', 'delete.png')
    copy = create_path('context', 'copy.png')
    add = create_path('context', 'add.png')

    add_db = create_path('metaprocess', 'add_database.png')
    close_db = create_path('metaprocess', 'close_database.png')
    cut = create_path('metaprocess', 'cut.png')
    duplicate = create_path('metaprocess', 'duplicate.png')
    graph_lmp = create_path('metaprocess', 'graph_linkedmetaprocess.png')
    graph_mp = create_path('metaprocess', 'graph_metaprocess.png')
    load_db = create_path('metaprocess', 'open_database.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')
    metaprocess = create_path('metaprocess', 'metaprocess.png')
    new = create_path('metaprocess', 'new_metaprocess.png')
    save_db = create_path('metaprocess', 'save_database.png')
    save_mp = create_path('metaprocess', 'save_metaprocess.png')

    debug = create_path('main', 'debug.png')
    forward = create_path('main', 'forward.png')
    right = create_path('main', 'right.png')
    left = create_path('main', 'left.png')
    backward = create_path('main', 'backward.png')
    key = create_path('main', 'key.png')
    search = create_path('main', 'search.png')
    switch = create_path('main', 'switch-state.png')
    ab = create_path('main', 'activitybrowser.png')


icons = Icons()
