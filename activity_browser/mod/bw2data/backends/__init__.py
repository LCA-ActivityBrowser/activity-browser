from bw2data.backends import *

from .base import SQLiteBackend
from .proxies import Activity, Exchange, ActivityDataset, ExchangeDataset

try:
    from bw2data.backends.peewee import sqlite3_lci_db
except:
    # we're running bw25
    pass

Node = Activity
Edge = Exchange
