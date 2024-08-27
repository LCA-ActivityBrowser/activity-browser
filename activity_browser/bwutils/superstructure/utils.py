# -*- coding: utf-8 -*-
import time
from logging import getLogger

import pandas as pd

from activity_browser.mod import bw2data as bd

log = getLogger(__name__)

# Different kinds of indexes, to allow for quick selection of data from
# the Superstructure DataFrame.
# TODO review if this can be made a list instead of pd.Index
SUPERSTRUCTURE = pd.Index(
    [
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
    ]
)


def edit_superstructure_for_string(
    superstructure=SUPERSTRUCTURE, sep="<br>", fhighlight=""
):
    """
    Produces a string format for the essential columns for the scenario difference files with html
    style formatting. Allows for different defined structures.

    Parameters
    ----------
    superstructure: the list of superstructure column headers (by default set to the SUPERSTRUCTURE index,
    this needs to have a defined __str__ operator
    sep: a short string that defines the separator for the column headers, by default this is the html line
    break <br>
    fhighlight: this is provided as a means to highlight the fields, by default this is empty (SHOULD NOT BE
    SET TO None), but could be set to "[]", where the first and last elements enclose the field

    Returns
    -------
    A formatted strign with the required file fields
    """
    text_list = ""
    for field in superstructure:
        text_list += (
            f"{fhighlight[0]}{field}{fhighlight[-1]}{sep}"
            if fhighlight
            else f"{field}{sep}"
        )
    return text_list


def guess_flow_type(row: pd.Series) -> str:
    """Given a series of input- and output keys, make a guess on the flow type."""
    if row.iat[0][0] == bd.config.biosphere:
        return "biosphere"
    elif row.iat[0] == row.iat[1]:
        return "production"
    else:
        return "technosphere"


def _time_it_(func):
    # TODO rename to non_protected name
    """
    For use as a wrapper to time the execution of functions using the python time library
    """

    def wrapper(*args):
        now = time.time()
        result = func(*args)
        log.info(f"{func} -- {time.time() - now}")
        return result

    return wrapper
