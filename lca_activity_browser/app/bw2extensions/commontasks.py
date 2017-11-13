# -*- coding: utf-8 -*-
# from __future__ import print_function, unicode_literals
# from eight import *

import brightway2 as bw



def format_activity_label(act, style='pnl'):
    try:
        a = bw.get_activity(act)

        if style == 'pnl':
            label = '\n'.join([a['reference product'],
                               a['name'],
                               a['location'],
                               ])
        elif style == 'pl':
            label = ', '.join([a['reference product'],
                               a['location'],
                               ])
        elif style == 'key':
            label = tuple([a['database'], a['code']])

        elif style == 'bio':
            label = ', '.join([a['name'],
                               str(a['categories']),
                               ])
        else:
            label = '\n'.join([a['reference product'],
                               a['name'],
                               a['location'],
                               ])
    except:
        return str(act)
    return label