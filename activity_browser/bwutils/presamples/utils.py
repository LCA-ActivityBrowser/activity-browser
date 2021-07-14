# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Iterable, List, Optional

import brightway2 as bw
from presamples import PresampleResource


def count_presample_packages() -> int:
    ps_dir = Path(bw.projects.dir).joinpath("presamples")
    return sum(1 for _ in ps_dir.iterdir()) if ps_dir.is_dir() else 0


def presamples_packages() -> Iterable:
    ps_dir = Path(bw.projects.dir).joinpath("presamples")
    return ps_dir.glob("*/datapackage.json") if ps_dir.is_dir() else []


def find_all_package_names() -> List[str]:
    """ Peek into the presamples folder of the current project and return
     all of the package names.

    If a package name is used more than once, all following packages with
    that name will have their id returned instead.
    """
    names = set()
    for p in presamples_packages():
        metadata = json.loads(p.read_text())
        name = metadata.get("name")
        exists_unique = name and name not in names
        names.add(name if exists_unique else metadata.get("id"))
    return sorted(names)


def get_package_path(name_id: str) -> Optional[Path]:
    """ Attempt to find the presamples package matching the name or id given.

    NOTE: If a non-unique name is given, it is possible the incorrect package
     is returned.
    """
    for p in presamples_packages():
        metadata = json.loads(p.read_text())
        if name_id in {metadata.get("name"), metadata.get("id")}:
            return p.parent


def remove_package(path: Path) -> bool:
    """ Attempt to remove a presamples package with the given path
    returns success.
    """
    ps_dir = Path(bw.projects.dir).joinpath("presamples")
    if path.parent == ps_dir and path.is_dir():
        for p in path.iterdir():
            p.unlink()
        path.rmdir()
        return True
    return False


def clear_resource_by_name(name_id: str) -> bool:
    """Attempts to clear a PresamplesResource object from the database."""
    obj = PresampleResource.get_or_none(name=name_id)
    if obj:
        db_tuple = next(db for db in bw.config.sqlite3_databases if db[0] == "campaigns.db")
        with db_tuple[1].atomic():
            PresampleResource.delete().where(PresampleResource.id == obj.id).execute()
        return True
    return False
