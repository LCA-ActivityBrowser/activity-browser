import ast
import os.path
from importlib.metadata import PackageNotFoundError, version
from logging import getLogger

from .utils import safe_link_fetch, sort_semantic_versions

log = getLogger(__name__)

# get AB version
try:
    __version__ = version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0"


def get_compatible_versions() -> list:
    """Get compatible versions of ecoinvent for this AB version.

    Reads this file on github repo: activity-browser/better_biosphere_handling/compatible_ei_versions.txt'.
    Converts file content to available ecoinvent versions for each version of AB.
    Finds the correct available versions for this AB version, if failing to read version,
    the lowest version in the file is chosen.
    """
    try:
        # read versions
        versions_URL = "https://raw.githubusercontent.com/LCA-ActivityBrowser/activity-browser/main/activity_browser/bwutils/ecoinvent_biosphere_versions/compatible_ei_versions.txt"
        page, error = safe_link_fetch(versions_URL)
        if not error:
            file = page.text
        else:
            # silently try a local fallback:
            log.debug(
                f"Reading online compatible ecoinvent versions failed "
                f"-attempting local fallback- with this error: {error}"
            )
            file_path = os.path.join(
                os.path.dirname(__file__),
                "bwutils",
                "ecoinvent_biosphere_versions",
                "compatible_ei_versions.txt",
            )
            with open(file_path, "r") as f:
                file = f.read()
        all_versions = ast.literal_eval(file)

        # select either the latest lower version available or if none available the lowest version for safety
        sorted_versions = sort_semantic_versions(all_versions.keys())
        for ab_version in sorted_versions:
            if sort_semantic_versions([__version__, ab_version])[0] == __version__:
                # current version is higher than or equal to tested AB version:
                ei_versions = all_versions[ab_version]
                break
        else:
            ei_versions = all_versions[sorted_versions[-1]]

        log.debug(
            f"Following versions of ecoinvent are compatible with AB {__version__}: {ei_versions}"
        )
        return ei_versions

    except Exception as error:
        log.debug(f"Reading local fallback failed with: {error}")
        return ["3.4", "3.5", "3.6", "3.7", "3.7.1", "3.8", "3.9", "3.9.1"]


__ei_versions__ = get_compatible_versions()
