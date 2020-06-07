# -*- coding: utf-8 -*-
import pandas as pd


# Different kinds of indexes, to allow for quick selection of data from
# the Superstructure DataFrame.
SUPERSTRUCTURE = pd.Index([
    "from activity name",
    "from reference product",
    "from location",
    "from categories",
    "from database",
    "from key",
    "to activity name",
    "to reference product",
    "to location",
    "to categories",
    "to database",
    "to key",
    "flow type",
])
EXCHANGE_KEYS = pd.Index(["from key", "to key"])
INDEX_KEYS = pd.Index(["from key", "to key", "flow type"])
FROM_ALL = pd.Index([
    "from activity name", "from reference product", "from location",
    "from categories", "from database", "from key"
])
TO_ALL = pd.Index([
    "to activity name", "to reference product", "to location", "to categories",
    "to database", "to key"
])



