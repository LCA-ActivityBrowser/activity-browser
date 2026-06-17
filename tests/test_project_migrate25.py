"""Tests for Brightway25 project migration."""

import bw2data as bd

from activity_browser.app.actions.project.project_migrate25 import MigrateThread
from fixtures.bw_helpers import write_method


def test_pre_process_methods_converts_legacy_tuple_cfs_to_activity_ids(basic_database):
    """Legacy CF keys (database, code) must be rewritten with Brightway activity ids."""
    elementary = basic_database.get("elementary")
    write_method(
        "legacy_method",
        [(elementary.key, 1.6)],
        process=False,
    )

    MigrateThread.pre_process_methods()

    loaded = list(bd.Method(("legacy_method",)).load())
    assert loaded == [(elementary.id, 1.6)]
    assert loaded[0][0] == bd.get_node(key=elementary.key).id


def test_pre_process_methods_preserves_regionalized_cfs(basic_database):
    elementary = basic_database.get("elementary")
    write_method(
        "regional_method",
        [(elementary.key, 1.6, "GLO")],
        process=False,
    )

    MigrateThread.pre_process_methods()

    loaded = list(bd.Method(("regional_method",)).load())
    assert loaded == [(elementary.id, 1.6, "GLO")]
