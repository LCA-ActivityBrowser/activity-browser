# -*- coding: utf-8 -*-
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
        if isinstance(act, tuple):
            return str(''.join(act))
        else:
            return str(act)
    return label
