from importlib.metadata import PackageNotFoundError, version

# get AB version
try:
    __version__ = version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0"

# supported EI versions
__ei_versions__ = ["3.4", "3.5", "3.6", "3.7", "3.7.1", "3.8", "3.9", "3.9.1"]
