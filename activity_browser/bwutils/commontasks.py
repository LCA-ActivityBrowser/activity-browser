import os
import hashlib
import textwrap
from datetime import datetime
from loguru import logger
from collections import OrderedDict

import arrow
import pandas as pd
import numpy as np

import bw2data as bd
from bw2data.parameters import ParameterBase, ProjectParameter, DatabaseParameter, ActivityParameter, Group
from bw2data.errors import UnknownObject

from functools import lru_cache

from .utils import Parameter

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


def shorten_label(text: str, max_length: int = 40) -> str:
    """Single-line label for axes/legends; use a tooltip for the full string."""
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "…"


def _activity_as_dict(act) -> dict:
    if hasattr(act, "as_dict"):
        return act.as_dict()
    return dict(act)


def reference_flow_parts(act) -> tuple[str, str, str, str]:
    """Return ``(product, process, location, database)`` for a reference-flow activity."""
    act_dict = _activity_as_dict(act)
    act_type = act_dict.get("type", "")
    product_types = tuple(getattr(bd.labels, "product_node_types", ("product", "waste")))

    if act_type in product_types:
        product = (
            act_dict.get("reference product")
            or act_dict.get("product")
            or act_dict.get("name", "")
        )
        process_name = ""
        processor = act_dict.get("processor")
        if processor:
            try:
                process_name = bd.get_activity(processor).get("name", "")
            except Exception:
                process_name = ""
    else:
        process_name = act_dict.get("name", "")
        product = act_dict.get("reference product")
        if not product:
            for exc in act_dict.get("exchanges") or []:
                if exc.get("type") == "production" and exc.get("amount", 0) > 0:
                    try:
                        ref_product, _, _, _ = reference_flow_parts(
                            bd.get_activity(exc["input"])
                        )
                        if ref_product:
                            product = ref_product
                            break
                    except Exception:
                        pass
        if not product:
            product = process_name or "Unknown"

    location = str(act_dict.get("location", "") or "")
    database = str(act_dict.get("database", "") or "")
    return product, process_name, location, database


def get_fu_label(
    act,
    amount: float | None = None,
    *,
    separator: str = " | ",
) -> str:
    """AB convention: product | process | location | database."""
    product, process_name, location, database = reference_flow_parts(act)
    parts = [product, process_name, location, database]
    if amount is not None:
        parts.append(f"{amount}")
    return separator.join(parts)


def get_method_label(method, *, separator: str = ", ") -> str:
    """AB convention: joined Brightway method tuple parts."""
    if isinstance(method, str):
        return method
    if not isinstance(method, (tuple, list)):
        return str(method)
    return separator.join(str(part) for part in method if part)


def exchange_part_label(node, *, include_database: bool = True) -> str:
    """Human-readable label for one exchange end (input or output part).

    For technosphere nodes: ``product | process [location] (database)``.
    For biosphere nodes: ``flow | categories (database)``.
    """
    node = refresh_node(node)
    if is_node_biosphere(node):
        flow_name = node.get("name", "")
        categories = node.get("categories")
        if isinstance(categories, (list, tuple)):
            category_text = ", ".join(str(c) for c in categories)
        else:
            category_text = str(categories or flow_name)
        database = node.get("database") or ""
        if include_database and database:
            return f"{flow_name} | {category_text} ({database})"
        return f"{flow_name} | {category_text}"

    product, process_name, location, database = reference_flow_parts(node)
    location_text = f" [{location}]" if location else ""
    database_text = f" ({database})" if database and include_database else ""
    return f"{product} | {process_name}{location_text}{database_text}"


def exchange_label(input_node, output_node, *, include_database: bool = True) -> str:
    """Full exchange label ``input --> output`` for tooltips and GSA metadata."""
    left = exchange_part_label(input_node, include_database=include_database)
    right = exchange_part_label(output_node, include_database=include_database)
    return f"{left} --> {right}"


def exchange_product_name(input_node) -> str:
    """Reference product or flow name for the exchange input side."""
    node = refresh_node(input_node)
    if is_node_biosphere(node):
        return node.get("name", "")
    product, _, _, _ = reference_flow_parts(node)
    return product


def exchange_consumer_parts(output_node) -> tuple[str, str, str]:
    """Return ``(process, location, database)`` for the exchange consumer (output)."""
    _, process, location, database = reference_flow_parts(refresh_node(output_node))
    return process, location, database


def cleanup_deleted_bw_projects() -> None:
    """Clean up the deleted projects from disk.

    NOTE: This cannot be done from within the AB.
    """
    n_dir = bd.projects.purge_deleted_directories()
    logger.info(f"Deleted {n_dir} unused project directories!")


def projects_by_last_opened():
    def key(ds):
        if not ds.data or "last_opened" not in ds.data:
            return 0
        date = datetime.fromisoformat(ds.data["last_opened"])

        return int(date.strftime("%Y%m%d%H%M%S"))

    projects = list(bd.projects)
    projects.sort(key=key, reverse=True)

    return projects



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

def database_is_locked(name: str) -> bool:
    """Returns True if the database is locked."""
    if not name in bd.databases:
        raise KeyError("Not an existing database:", name)
    return bd.databases[name].get("read_only", True)

def database_is_legacy(name: str) -> bool:
    """Returns True if the database is sqlite."""
    if not name in bd.databases:
        raise KeyError("Not an existing database:", name)

    database = bd.Database(name)

    if database.backend not in ["sqlite", "functional_sqlite"]:
        raise ValueError("Database backend must be sqlite or functional_sqlite")

    return database.backend == "sqlite"

def is_technosphere_db(db_name: str) -> bool:
    """Returns True if database describes the technosphere, False if it describes a biosphere."""
    if not db_name in bd.databases:
        raise KeyError("Not an existing database:", db_name)
    # This code seems incorrect, just return True for now
    return True


def get_writable_databases() -> list[str]:
    """Get the list of databases that are not locked."""
    names = []
    for name in bd.databases:
        if bd.databases[name].get("read_only", True):
            continue
        if database_is_locked(name):
            continue
        names.append(name)
    return sorted(names)


def count_database_records(name: str) -> int:
    """To account for possible brightway database types that do not implement
    the __len__ method.
    """
    from activity_browser.app import metadata
    try:
        return len(metadata.dataframe.loc[name])
    except KeyError:
        return 0



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
    "Functional": "functional",
}

bw_keys_to_AB_names = {v: k for k, v in AB_names_to_bw_keys.items()}


def get_activity_name(key, str_length=22):
    return ",".join(key.get("name", "").split(",")[:3])[:str_length]


@lru_cache(maxsize=1)
def biosphere_node_types() -> frozenset[str]:
    """Elementary-flow node types from Brightway ``typo_settings`` vs ``labels.lci_node_types``."""
    from bw2data.configuration import labels, typo_settings

    return frozenset(typo_settings.node_types) - frozenset(labels.lci_node_types)


def is_node_product_or_waste(node: tuple | int | bd.Node) -> bool:
    return is_node_product(node) or is_node_waste(node)

def is_node_product(node: tuple | int | bd.Node) -> bool:
    node = refresh_node(node)
    raw_type = node._document.type

    if raw_type in ["product", "processwithreferenceproduct"]:
        return True

    if raw_type == "process" and len(node.upstream(kinds=["production"])):
        return True

    return False

def is_node_waste(node: tuple | int | bd.Node) -> bool:
    node = refresh_node(node)
    raw_type = node._document.type

    if raw_type == "waste":
        return True

    return False


def is_node_biosphere(node: tuple | int | bd.Node) -> bool:
    """True if *node* is an elementary flow (biosphere node, not technosphere)."""
    node = refresh_node(node)
    return node._document.type in biosphere_node_types()

def is_node_process(node: tuple | int | bd.Node) -> bool:
    node = refresh_node(node)
    raw_type = node._document.type

    if raw_type in ["process", "nonfunctional", "multifunctional", "processwithreferenceproduct"]:
        return True
    return False


def refresh_node(node: tuple | int | np.int64 | bd.Node) -> bd.Node:
    if isinstance(node, bd.Node):
        node = bd.get_node(id=node.id)
    elif isinstance(node, tuple):
        node = bd.get_node(key=node)
    elif isinstance(node, (int, np.int64)):
        node = bd.get_node(id=node)
    else:
        raise ValueError("Activity must be either a tuple, int or Node instance")
    return node


def refresh_node_or_none(node: tuple | int | bd.Node) -> bd.Node | None:
    try:
        return refresh_node(node)
    except (ValueError, UnknownObject):
        return None


def refresh_parameter(parameter: tuple | Parameter | ParameterBase):
    # construct mock-parameter if it is a parameter key (group, name)
    if isinstance(parameter, tuple) and len(parameter) == 2:
        if parameter[0] == "project":
            parameter = Parameter(parameter[1], parameter[0], None, None, "project")
        elif parameter[0] in bd.databases:
            parameter = Parameter(parameter[1], parameter[0], None, None, "database")
        else:
            parameter = Parameter(parameter[1], parameter[0], None, None, "activity")

    # get the newest peewee model from the database
    if isinstance(parameter, Parameter):
        raw = parameter.to_peewee_model()
    elif isinstance(parameter, ParameterBase):
        raw = parameter.get_by_id(parameter.id)
    else:
        raise ValueError("Unknown parameter type")

    # construct a new Parameter-type from the peewee model
    if isinstance(raw, ProjectParameter):
        return Parameter(raw.dict.pop("name"), "project", raw.dict.get("amount"), raw.dict, "project")
    elif isinstance(raw, DatabaseParameter):
        return Parameter(raw.dict.pop("name"), raw.database, raw.dict.get("amount"), raw.dict, "database")
    elif isinstance(raw, ActivityParameter):
        return Parameter(raw.dict.pop("name"), raw.group, raw.dict.get("amount"), raw.dict, "activity")
    else:
        raise ValueError("Unknown parameter type")


def parameters_in_scope(
        node: tuple | int | bd.Node = None,
        parameter: tuple | Parameter | ParameterBase = None
) -> dict[str, Parameter]:
    if (not node and not parameter) or (node and parameter):
        raise ValueError("Supply either node or parameter")
    if node:
        node = refresh_node(node)
        database = node["database"]
        group = node_group(node)
    else:  # if parameter
        parameter = refresh_parameter(parameter)
        group = parameter.group
        if group == "project":
            database = None
        elif group in bd.databases:
            database = group
        else:
            database = ActivityParameter.get_or_none(group=group).database

    data = OrderedDict()

    for name, param in ProjectParameter.load().items():
        data[name] = Parameter(name, "project", param["amount"], param, "project")

    for name, param in DatabaseParameter.load(database).items():
        if name in data:
            del data[name]  # the variable is overwritten in the scope chain
        data[name] = Parameter(name, database, param["amount"], param, "database")

    group_deps = Group.get_or_none(name=group).order + [group] if group else []

    for dep in group_deps:
        for name, param in ActivityParameter.load(dep).items():
            if name in data:
                del data[name]  # the variable is overwritten in the scope chain
            data[name] = Parameter(name, dep, param.get("amount"), param, "activity")

    return data


def node_group(node: tuple | int | bd.Node) -> str | None:
    """Returns the group of the node, or None if it does not have a group."""
    node = refresh_node(node)
    ap = ActivityParameter.get_or_none(database=node["database"], code=node["code"])
    return ap.group if ap else None


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


@lru_cache(maxsize=2048)
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
    from activity_browser.app import metadata
    
    db, code = key
    meta = metadata.get_database_metadata(db)
    if "_copy" in code:
        code = code.split("_copy")[0]
    copies = (
        meta["key"]
        .apply(lambda x: x[1] if code in x[1] and "_copy" in x[1] else None)
        .dropna()
        .to_list()
        if not meta.empty
        else []
    )
    if not copies:
        return f"{code}_copy1"
    n = max((int(c.split("_copy")[1]) for c in copies))
    return f"{code}_copy{n + 1}"


# EXCHANGES
def refresh_edge(edge: int | bd.Edge) -> bd.Edge:
    if isinstance(edge, bd.Edge):
        edge = edge.__class__(bd.Edge.ORMDataset.get_by_id(edge.id))
    elif isinstance(edge, int):
        # Edge is just the ID
        # need to go at it using a workaround to get the edge class right through the owner activity
        owner = bd.Edge(bd.Edge.ORMDataset.get_by_id(edge)).output
        for candidate in owner.edges():
            if candidate.id == edge:
                return candidate
    else:
        raise ValueError("Edge must be either an int or Edge instance")
    return edge


def refresh_edge_or_none(edge: int | bd.Edge) -> bd.Edge | None:
    try:
        return refresh_edge(edge)
    except (ValueError, UnknownObject):
        return None


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
            logger.error(
                "Something did not work with the following exchange: {}. It was removed from the list.".format(
                    exc
                )
            )
    return data


def exchanges_to_sdf(exchanges: list[dict]) -> pd.DataFrame:
    data = get_exchanges_in_scenario_difference_file_notation(exchanges)
    return pd.DataFrame(data)


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


# Common tasks
def savefilepath(
    default_file_name: str = "AB_file", file_filter: str = "All Files (*.*)"
):
    """A central function to get a safe file path."""
    from qtpy import QtWidgets

    from activity_browser.bwutils import filesystem

    safe_name = bd.utils.safe_filename(default_file_name, add_hash=False)
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent=None,
        caption="Choose location for saving",
        dir=os.path.join(filesystem.get_project_path(), safe_name),
        filter=file_filter,
    )
    return filepath


def get_templates() -> dict:
    import platformdirs, os

    base_dir = platformdirs.user_data_dir(appname="ActivityBrowser", appauthor="ActivityBrowser")
    template_dir = os.path.join(base_dir, "templates")
    os.makedirs(template_dir, exist_ok=True)

    collection = {}

    for file in os.listdir(template_dir):
        if file.endswith(".tar.gz"):
            collection[file[:-7]] = os.path.join(template_dir, file)

    return collection

def nodes_to_excel(nodes: list[tuple | int | bd.Node]) -> str:
    """Convert a list of nodes to an HTML table suitable for Excel."""
    from .exporters import ABCSVFormatter
    nodes = [refresh_node(n) for n in nodes]
    databases = set(n["database"] for n in nodes)
    if len(databases) > 1:
        raise ValueError("All nodes must be from the same database")
    db_name = databases.pop()
    formatter = ABCSVFormatter(db_name, nodes)
    data = formatter.get_formatted_data(sections=["activities", "exchanges"])

    html_rows = []
    for row in data:
        if isinstance(row, list):
            # Bold formatting for lists with nowrap
            cells = "".join(f'<td style="white-space: nowrap;"><b>{str(i)}</b></td>' for i in row)
        else:
            # Regular formatting for tuples with nowrap
            cells = "".join(f'<td style="white-space: nowrap;">{str(i)}</td>' for i in row)
        html_rows.append(f"<tr>{cells}</tr>")

    return f"<table>{''.join(html_rows)}</table>"
