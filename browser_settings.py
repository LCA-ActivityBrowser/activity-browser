#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file contains various settings used in the Activity Browser and its extensions.
"""

# ACTIVITY EDITOR
read_only_databases = \
    ["ecoinvent 2.2", "ecoinvent 2.2 multioutput", "ecoinvent 3.01 default",
     "ecoinvent 3.01 cutoff", "ecoinvent 3.01 consequential", "ecoinvent 3.1 default",
     "ecoinvent 3.1 cutoff", "ecoinvent 3.1 consequential", "biosphere", "biosphere3"]

# Initial positions of docks: (area in main window, position if tabbed)
# NOT YET USED
left, right, top, bottom = 1, 2, 4, 8  # integers corresponding to QtCore.Qt.LeftDockWidgetArea etc.
dock_positions_at_start = {
    left: ['Technosphere', 'LCIA'],
    right: ['Databases', 'Search', 'Biosphere'],
    top: [],
    bottom: []
}

# RGB coloring of table contents
table_item_colors = {
    'product': (0, 0, 204),
    'name': (0, 0, 0),
    'amount': (0, 0, 0),
    'unit': (153, 0, 153),
    'location': (0, 102, 51),
    'database': (0, 0, 0),
}