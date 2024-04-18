from bw2data import *

from .project import projects
from .meta import databases, calculation_setups

from .backends import convert_backend
from .utils import get_activity


# import importlib
# for x in [x for x in dir(__import__("bw2data")) if x not in globals()]:
#     importlib.import_module("bw2data." + x)

