"""Dependency-free checks for progress messages shown by worker threads."""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "activity_browser"
PROGRESS_SOURCES = (
    PACKAGE / "mod" / "bw2io" / "__init__.py",
    PACKAGE / "mod" / "bw2io" / "ecoinvent.py",
    PACKAGE / "mod" / "bw2io" / "migrations.py",
    PACKAGE / "mod" / "bw2io" / "importers" / "ecospold2_biosphere.py",
    PACKAGE / "mod" / "ecoinvent_interface" / "release.py",
)


def qualified_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def contains_call(node, name):
    return any(
        isinstance(part, ast.Call)
        and qualified_name(part.func).rsplit(".", 1)[-1] == name
        for part in ast.walk(node)
    )


def test_worker_progress_titles_and_info_messages_are_translated():
    progress_titles = []
    info_messages = []

    for path in PROGRESS_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = qualified_name(node.func).rsplit(".", 1)[-1]
            if callee in {"ProgBar", "prog_bar"}:
                progress_titles.extend(
                    keyword.value for keyword in node.keywords if keyword.arg == "title"
                )
            elif callee == "info" and node.args:
                info_messages.append(node.args[0])

    assert progress_titles
    assert info_messages
    assert all(contains_call(node, "_") for node in progress_titles)
    assert all(contains_call(node, "_") for node in info_messages)


def test_migration_progress_labels_use_one_translated_template():
    path = PACKAGE / "mod" / "bw2io" / "migrations.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    title_assignments = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == "title"
            for target in node.targets
        )
    ]

    assert len(title_assignments) == 12
    assert all(contains_call(node, "_migration_title") for node in title_assignments)


def test_progress_catalog_preserves_dynamic_identifiers():
    catalog = json.loads(
        (PACKAGE / "translations" / "zh_CN" / "progress.json").read_text(
            encoding="utf-8"
        )
    )

    assert catalog["Creating migration: {migration}"].count("{migration}") == 1
    assert catalog["Installing biosphere version {version}"].count("{version}") == 1
    assert catalog["Applying biosphere patch: {patch}"].count("{patch}") == 1
    close_match = catalog[
        "Using close match {match} for predicted filename {filename}"
    ]
    assert close_match.count("{match}") == 1
    assert close_match.count("{filename}") == 1


def test_logging_progress_handler_formats_records_itself():
    source = (PACKAGE / "ui" / "threading.py").read_text(encoding="utf-8")
    assert "record.getMessage()" in source
    assert "record.message" not in source
