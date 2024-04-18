from bw2data.utils import *
from activity_browser.brightway.bw2data.backends.peewee.proxies import Activity


def get_activity(key) -> Activity:
    import bw2data
    return bw2data.utils.get_activity(key)
