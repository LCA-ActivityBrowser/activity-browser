# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
import time

import logging
from activity_browser.logger import ABHandler

logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)

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


def guess_flow_type(row: pd.Series) -> str:
    """Given a series of input- and output keys, make a guess on the flow type.
    """
    if row.iat[0][0] == bw.config.biosphere:
        return "biosphere"
    elif row.iat[0] == row.iat[1]:
        return "production"
    else:
        return "technosphere"

def _time_it_(func):
    """
    For use as a wrapper to time the execution of functions using the python time library
    """
    def wrapper(*args):
        now = time.time()
        result = func(*args)
        log.info(f"{func} -- " + str(time.time() - now))
        return result
    return wrapper