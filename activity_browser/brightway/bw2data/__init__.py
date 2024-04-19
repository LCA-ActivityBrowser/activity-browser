from bw2data import *

from .project import projects
from .meta import databases, calculation_setups, methods
from .method import Method
from .utils import get_activity
from .parameters import parameters


# import importlib
# for x in [x for x in dir(__import__("bw2data")) if x not in globals()]:
#     importlib.import_module("bw2data." + x)

