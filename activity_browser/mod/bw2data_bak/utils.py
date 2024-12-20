from bw2data.utils import *

from bw2data.backends import Activity


def get_activity(key) -> Activity:
    """Re-init of get_activity to show the IDE that we're returning a patched activity"""
    import bw2data

    return bw2data.utils.get_activity(key)
