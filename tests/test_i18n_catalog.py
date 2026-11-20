"""Dependency-free integrity checks for the Simplified Chinese catalog.

These tests deliberately use only the Python standard library.  They can run on
a clean checkout even when Qt and Brightway are not installed.
"""

import ast
from collections import Counter
import json
from pathlib import Path
import re
from string import Formatter


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "activity_browser"
CATALOG_ROOT = PACKAGE_ROOT / "translations" / "zh_CN"

QT_STANDARD_TEXT = {
    "&Cancel",
    "&Finish",
    "&Next >",
    "&No",
    "&OK",
    "&Save",
    "&Yes",
    "< &Back",
    "Abort",
    "Apply",
    "Cancel",
    "Close",
    "Discard",
    "Help",
    "Ignore",
    "No",
    "OK",
    "Open",
    "Reset",
    "Restore Defaults",
    "Retry",
    "Save",
    "Save All",
    "Yes",
}


# These calls intentionally translate text selected at runtime.  Keeping the
# whitelist explicit makes new dynamic calls visible in review: each runtime
# source must itself ultimately come from a finite, translated set.
DYNAMIC_TRANSLATION_CALLS = {
    ("activity_browser/actions/base.py", "cls.text"),
    ("activity_browser/actions/base.py", "tooltip"),
    ("activity_browser/actions/parameter/parameter_new.py", "s"),
    ("activity_browser/bwutils/superstructure/file_dialogs.py", "title"),
    ("activity_browser/bwutils/superstructure/file_dialogs.py", "message"),
    (
        "activity_browser/bwutils/superstructure/file_dialogs.py",
        "obj.button1.text()",
    ),
    (
        "activity_browser/bwutils/superstructure/file_dialogs.py",
        "obj.button2.text()",
    ),
    ("activity_browser/i18n.py", "_LANGUAGE_LABELS[code]"),
    ("activity_browser/layouts/panels/left.py", "source_label"),
    ("activity_browser/layouts/panels/right.py", "source_label"),
    ("activity_browser/layouts/tabs/LCA_results_tabs.py", "field"),
    ("activity_browser/layouts/tabs/parameters.py", "name"),
    # These values are translated only within the recognized, fixed leading
    # Score/Total + Rest rows; tests/ui/test_semantic_ids.py covers collisions.
    ("activity_browser/ui/figures.py", "label"),
    ("activity_browser/ui/figures.py", "raw_label"),
    ("activity_browser/ui/figures.py", "unit"),
    ("activity_browser/ui/tables/models/base.py", "value"),
    ("activity_browser/ui/tables/models/base.py", "str(value)"),
    ("activity_browser/ui/tables/delegates/uncertainty.py", "description"),
    (
        "activity_browser/ui/tables/models/base.py",
        "str(self.HEADERS[column])",
    ),
    ("activity_browser/ui/web/base.py", "self.HELP_TEXT"),
    ("activity_browser/ui/web/base.py", "self.PAGE_TITLE"),
    ("activity_browser/ui/web/base.py", "line"),
    (
        "activity_browser/ui/web/navigator.py",
        "'Current mode: Expansion' if self._expansion_mode else 'Current mode: Navigation'",
    ),
    (
        "activity_browser/ui/wizards/db_export_wizard.py",
        "self.FILTERS[self.selected_exporter]",
    ),
    ("activity_browser/ui/wizards/db_import_wizard.py", "option[0]"),
    ("activity_browser/ui/wizards/settings_wizard.py", "theme_code"),
    ("activity_browser/ui/wizards/uncertainty.py", "ud.description"),
    ("activity_browser/ui/tables/views.py", "file_filter or self.ALL_FILTER"),
    ("activity_browser/utils.py", "file_filter"),
}


def _catalog_pairs():
    """Yield every source/translation pair without hiding duplicate JSON keys."""

    fragments = sorted(CATALOG_ROOT.glob("*.json"))
    assert fragments, f"No catalog fragments found in {CATALOG_ROOT}"

    for path in fragments:
        pairs = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=lambda value: value
        )
        assert isinstance(pairs, list), f"{path} must contain one JSON object"
        for pair in pairs:
            assert isinstance(pair, tuple) and len(pair) == 2, (
                f"{path} must map source strings directly to translated strings"
            )
            yield path, pair[0], pair[1]


def _merged_catalog():
    merged = {}
    origins = {}
    conflicts = []

    for path, source, translation in _catalog_pairs():
        if source in merged and merged[source] != translation:
            conflicts.append(
                f"{source!r}: {origins[source].name}={merged[source]!r}; "
                f"{path.name}={translation!r}"
            )
        else:
            merged[source] = translation
            origins[source] = path

    assert not conflicts, "Conflicting catalog entries:\n" + "\n".join(conflicts)
    return merged


def _format_fields(value):
    return [
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name is not None
    ]


def _translation_calls():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        relative_path = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_"
            ):
                continue
            assert node.args, f"{relative_path}:{node.lineno}: _() has no source text"
            yield relative_path, node.lineno, node.args[0]


def test_catalog_fragments_merge_without_conflicts():
    catalog = _merged_catalog()
    assert catalog, "The merged Simplified Chinese catalog is empty"
    assert catalog["Categories"] == "类别"


def test_catalog_sources_and_translations_are_non_empty_strings():
    invalid = []
    for path, source, translation in _catalog_pairs():
        if not isinstance(source, str) or not source.strip():
            invalid.append(f"{path.name}: invalid source {source!r}")
        if not isinstance(translation, str) or not translation.strip():
            invalid.append(f"{path.name}: {source!r} has an empty translation")

    assert not invalid, "Invalid catalog entries:\n" + "\n".join(invalid)


def test_catalog_placeholders_are_named_and_preserved():
    problems = []
    for path, source, translation in _catalog_pairs():
        try:
            source_fields = _format_fields(source)
            translated_fields = _format_fields(translation)
        except ValueError as error:
            problems.append(f"{path.name}: {source!r}: malformed braces ({error})")
            continue

        for field_name in source_fields + translated_fields:
            root_name = re.split(r"[.\[]", field_name, maxsplit=1)[0]
            if not root_name or root_name.isdecimal():
                problems.append(
                    f"{path.name}: {source!r}: positional placeholder {field_name!r}"
                )

        if Counter(source_fields) != Counter(translated_fields):
            problems.append(
                f"{path.name}: {source!r}: source placeholders {source_fields!r}, "
                f"translation placeholders {translated_fields!r}"
            )

    assert not problems, "Catalog placeholder errors:\n" + "\n".join(problems)


def test_every_static_translation_literal_has_a_chinese_entry():
    catalog = _merged_catalog()
    missing = []
    for path, line, expression in _translation_calls():
        try:
            source = ast.literal_eval(expression)
        except (ValueError, TypeError, SyntaxError):
            continue
        if not isinstance(source, str):
            missing.append(f"{path}:{line}: non-string literal {source!r}")
        elif source not in catalog:
            missing.append(f"{path}:{line}: {source!r}")

    assert not missing, "Static _() strings missing from zh_CN:\n" + "\n".join(missing)


def test_dynamic_translation_calls_are_explicitly_whitelisted():
    actual = set()
    for path, _line, expression in _translation_calls():
        try:
            ast.literal_eval(expression)
        except (ValueError, TypeError, SyntaxError):
            actual.add((path, ast.unparse(expression)))

    unexpected = sorted(actual - DYNAMIC_TRANSLATION_CALLS)
    stale = sorted(DYNAMIC_TRANSLATION_CALLS - actual)
    assert not unexpected and not stale, (
        "Dynamic _() call whitelist is out of date.\n"
        f"Unexpected calls: {unexpected!r}\n"
        f"Stale whitelist entries: {stale!r}"
    )


def test_catalog_files_are_utf8_and_qt_standard_text_has_json_fallbacks():
    for path in sorted(CATALOG_ROOT.glob("*.json")):
        path.read_bytes().decode("utf-8")

    catalog = _merged_catalog()
    assert QT_STANDARD_TEXT <= set(catalog)
    assert all(catalog[source] != source for source in QT_STANDARD_TEXT)


def test_bootstrap_order_and_release_resource_declarations():
    bootstrap = (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8")
    assert bootstrap.index("translation_manager.install") < bootstrap.index(
        "from .layouts.main import MainWindow"
    )

    # i18n is a leaf module in the Activity Browser import graph.  Settings can
    # import it safely while activity_browser.__init__ is still starting up.
    i18n_tree = ast.parse((PACKAGE_ROOT / "i18n.py").read_text(encoding="utf-8"))
    internal_imports = [
        node
        for node in ast.walk(i18n_tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("activity_browser")
    ]
    assert internal_imports == []

    setup_source = (ROOT / "setup.py").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    package_data_declaration = (
        '"activity_browser.translations": '
        '["*.json", "*.qm", "*/*.json", "*/*.qm"]'
    )
    assert package_data_declaration in setup_source
    assert "recursive-include activity_browser *.json" in manifest
