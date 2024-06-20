import hashlib
import textwrap

import arrow

from activity_browser import log
from activity_browser.mod import bw2data as bd

from .metadata import AB_metadata

"""
bwutils is a collection of methods that build upon brightway2 and are generic enough to provide here so that we avoid 
re-typing the same code in different parts of the Activity Browser.

When adding new methods, please use the sections below (or add a new section, if required).
"""


# Formatting
def wrap_text(string: str, max_length: int = 80) -> str:
    """Wrap the label making sure that key and name are in 2 rows.

    idea from https://stackoverflow.com/a/39134215/4929813
    """

    def fold(line: str) -> str:
        return textwrap.fill(
            line, width=max_length, break_long_words=True, replace_whitespace=False
        )

    return "\n".join(map(fold, string.splitlines()))


def format_activity_label(key, style="pnl", max_length=40):
    try:
        act = bd.get_activity(key)

        if style == "pnl":
            label = "\n".join(
                [
                    act.get("reference product", ""),
                    act.get("name", ""),
                    str(act.get("location", "")),
                ]
            )
        elif style == "pnl_":
            label = " | ".join(
                [
                    act.get("reference product", ""),
                    act.get("name", ""),
                    str(act.get("location", "")),
                ]
            )
        elif style == "pnld":
            label = " | ".join(
                [
                    act.get("reference product", ""),
                    act.get("name", ""),
                    str(act.get("location", "")),
                    act.get("database", ""),
                ]
            )
        elif style == "pl":
            label = ", ".join(
                [
                    act.get("reference product", "") or act.get("name", ""),
                    str(act.get("location", "")),
                ]
            )
        elif style == "key":
            label = str(act.key)  # safer to use key, code does not always exist

        elif style == "bio":
            label = ",\n".join([act.get("name", ""), str(act.get("categories", ""))])
        else:
            label = "\n".join(
                [
                    act.get("reference product", ""),
                    act.get("name", ""),
                    str(act.get("location", "")),
                ]
            )
    except:
        if isinstance(key, tuple):
            return wrap_text(str("".join(key)))
        else:
            return wrap_text(str(key))
    return wrap_text(label, max_length=max_length)


def cleanup_deleted_bw_projects() -> None:
    """Clean up the deleted projects from disk.

    NOTE: This cannot be done from within the AB.
    """
    n_dir = bd.projects.purge_deleted_directories()
    log.info("Deleted {} unused project directories!".format(n_dir))


# Database
def get_database_metadata(name):
    """Returns a dictionary with database meta-information."""
    d = dict()
    d["Name"] = name
    d["Depends"] = "; ".join(bd.databases[name].get("depends", []))
    dt = bd.databases[name].get("modified", "")
    if dt:
        dt = arrow.get(dt).humanize()
    d["Last modified"] = dt
    return d


def is_technosphere_db(db_name: str) -> bool:
    """Returns True if database describes the technosphere, False if it describes a biosphere."""
    if not db_name in bd.databases:
        raise KeyError("Not an existing database:", db_name)
    db = bd.Database(db_name)
    if len(db) == 0:
        return True
    act = db.random()
    if act is None or act.get("type", "process") == "process":
        return True
    else:
        return False


def is_technosphere_activity(activity: bd.Node) -> bool:
    """Avoid database lookups by testing the activity for a type, calls the
    above method if the field does not exist.
    """
    if "type" not in activity:
        return is_technosphere_db(activity.key[0])
    return activity.get("type") == "process"


def count_database_records(name: str) -> int:
    """To account for possible brightway database types that do not implement
    the __len__ method.
    """
    db = bd.Database(name)
    try:
        return len(db)
    except TypeError as e:
        log.error("{}. Counting manually".format(e))
        return sum(1 for _ in db)


# Activity
AB_names_to_bw_keys = {
    "Amount": "amount",
    "Product": "reference product",
    "Activity": "name",
    "Unit": "unit",
    "Location": "location",
    "Database": "database",
    "Uncertainty": "uncertainty type",
    "Formula": "formula",
    "Categories": "categories",
    "Type": "type",
    "Comment": "comment",
}

bw_keys_to_AB_names = {v: k for k, v in AB_names_to_bw_keys.items()}


def get_activity_name(key, str_length=22):
    return ",".join(key.get("name", "").split(",")[:3])[:str_length]


def clean_activity_name(activity_name: str) -> str:
    """Takes a given activity name and remove or replace all characters
    not allowed to be in there.

    Use this when creating parameters, as there are specific characters not
    allowed to be in parameter names.

    These are ' -,.%[]'
    Integers are also removed aggressively, there are allowed, but not
    at the start of a parameter name.
    """
    remove = ",.%[]()0123456789"
    replace = " -"
    # Remove invalid characters
    for char in remove:
        if char in activity_name:
            activity_name = activity_name.replace(char, "")
    # Replace spacing and dashes with underscores
    for char in replace:
        if char in activity_name:
            activity_name = activity_name.replace(char, "_")
    # strip underscores from start of string
    activity_name = activity_name.lstrip("_")
    return activity_name


def build_activity_group_name(key: tuple, name: str = None) -> str:
    """Constructs a group name unique to a given bw activity.

    If given a `name`, use that instead of looking up the activity name.

    NOTE: The created group name is not easy for users to understand, so hide
    it from them where possible.
    """
    simple_hash = hashlib.md5(":".join(key).encode()).hexdigest()
    if name:
        return "{}_{}".format(name, simple_hash)
    act = bd.get_activity(key)
    clean = clean_activity_name(act.get("name"))
    return "{}_{}".format(clean, simple_hash)


def identify_activity_type(activity):
    """Return the activity type based on its naming."""
    name = activity["name"]
    if "treatment of" in name:
        return "treatment"
    elif "market for" in name:
        # if not "to generic" in name:  # these are not markets, but also transferring activities
        return "market"
    elif "market group" in name:
        # if not "to generic" in name:
        return "marketgroup"
    else:
        return "production"


def generate_copy_code(key: tuple) -> str:
    """Generate a new code to use when copying an activity"""
    db, code = key
    metadata = AB_metadata.get_database_metadata(db)
    if "_copy" in code:
        code = code.split("_copy")[0]
    copies = (
        metadata["key"]
        .apply(lambda x: x[1] if code in x[1] and "_copy" in x[1] else None)
        .dropna()
        .to_list()
        if not metadata.empty
        else []
    )
    if not copies:
        return f"{code}_copy1"
    n = max((int(c.split("_copy")[1]) for c in copies))
    return f"{code}_copy{n + 1}"


# EXCHANGES
def get_exchanges_in_scenario_difference_file_notation(exchanges):
    """From a list of exchanges get the information needed for the scenario difference (SDF) file that is used in
    conjunction with the superstructure approach. This is a convenience function to export data from the AB in a format
    suitable for the SDF."""
    data = []
    for exc in exchanges:
        try:
            from_act = bd.get_activity(exc.get("input"))
            to_act = bd.get_activity(exc.get("output"))

            row = {
                "from activity name": from_act.get("name", ""),
                "from reference product": from_act.get("reference product", ""),
                "from location": from_act.get("location", ""),
                "from categories": from_act.get("categories", ""),
                "from database": from_act.get("database", ""),
                "from key": from_act.key,
                "to activity name": to_act.get("name", ""),
                "to reference product": to_act.get("reference product", ""),
                "to location": to_act.get("location", ""),
                "to categories": to_act.get("categories", ""),
                "to database": to_act.get("database", ""),
                "to key": to_act.key,
                "flow type": exc.get("type", ""),
                "amount": exc.get("amount", ""),
            }
            data.append(row)

        except:
            # The input activity does not exist. remove the exchange.
            log.error(
                "Something did not work with the following exchange: {}. It was removed from the list.".format(
                    exc
                )
            )
    return data


def get_exchanges_from_a_list_of_activities(
    activities: list, as_keys: bool = False
) -> list:
    """Get all exchanges in a list of activities."""
    if as_keys:
        activities = [bd.get_activity(key) for key in activities]
    exchanges = []
    for act in activities:
        for exc in act.exchanges():
            exchanges.append(exc)
    return exchanges


# LCIA
def unit_of_method(method: tuple) -> str:
    """Attempt to return the unit of the given method."""
    assert method in bd.methods
    return bd.methods[method].get("unit", "unit")


def get_LCIA_method_name_dict(keys: list) -> dict:
    """Impact categories in brightway2 are stored in tuples, which is
    unpractical for display in, e.g. dropdown menus.

    Returns a dictionary with
        keys: comma separated strings
        values: brightway2 method tuples
    """
    return {", ".join(key): key for key in keys}
