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