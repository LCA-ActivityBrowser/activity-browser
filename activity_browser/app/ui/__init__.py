# -*- coding: utf-8 -*-
"""the activity_cache dict contains activities which are currently open as tabs on the interface
activities are uniquely identified in BW with a tuple of (database, code)
The code of an activity is user-defined or an MD5 hash https://docs.brightwaylca.org/intro.html#uniquely-identifying-activities
These bw tuples are used as keys for the activity_cache.
The dictionary values are instances of ActivityDetailsTab()
"""
activity_cache = {}



