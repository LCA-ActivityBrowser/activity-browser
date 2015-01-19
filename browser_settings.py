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

default_LCIA_method = (u'IPCC 2013', u'climate change', u'GWP 100a')

# Initial positions of docks: (area in main window, position if tabbed)
# NOT YET USED
left, right, top, bottom = 1, 2, 4, 8  # integers corresponding to QtCore.Qt.LeftDockWidgetArea etc.
dock_positions_at_start = {
    left: ['Technosphere', 'LCIA'],
    right: ['Databases', 'Search', 'Biosphere'],
    top: [],
    bottom: []
}
