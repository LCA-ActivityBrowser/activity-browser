import sys

# This patch fixes a bug on Python 3.10 where shiboken6 patches the typing module with a broken Self type. Only way to
# fix it is to patch it ourselves first.
if sys.version_info[1] < 11:
    import typing
    if hasattr(typing, "Self"): # if Self has already been patched into typing, delete it first
        del typing.Self
    import typing_extensions
    setattr(typing, "Self", typing_extensions.Self)

try:
    import PySide6
except ImportError:
    import qtpy

from .ui.application import application
from .signals import signals

def run_activity_browser():
    from .__main__ import run_activity_browser
