import ast
import json
import string
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WIZARD_DIR = ROOT / "activity_browser" / "ui" / "wizards"
WIZARD_FILES = tuple(
    WIZARD_DIR / name
    for name in (
        "uncertainty.py",
        "db_export_wizard.py",
        "project_setup_wizard.py",
        "plugins_manager_wizard.py",
    )
)
CATALOG_FILE = (
    ROOT / "activity_browser" / "translations" / "zh_CN" / "wizards_misc.json"
)


def _literal_translation_sources(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    sources = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_"
            and node.args
        ):
            continue
        try:
            source = ast.literal_eval(node.args[0])
        except (ValueError, TypeError):
            continue
        if isinstance(source, str):
            sources.add(source)
    return sources


def test_misc_wizard_catalog_covers_fixed_ui_sources():
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    sources = set().union(
        *(_literal_translation_sources(path) for path in WIZARD_FILES)
    )
    # These filters are selected by a stable exporter ID before translation.
    sources.update(
        {
            "BW2Package Files (*.bw2package);; All Files (*.*)",
            "Excel Files (*.xlsx);; All Files (*.*)",
        }
    )

    assert sources <= catalog.keys()


def test_misc_wizard_translation_placeholders_match_sources():
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    formatter = string.Formatter()

    def fields(value):
        return sorted(
            field for _, field, _, _ in formatter.parse(value) if field is not None
        )

    for source, translation in catalog.items():
        assert fields(source) == fields(translation), source


def test_misc_wizard_catalog_has_no_conflicts_with_other_fragments():
    catalog_dir = CATALOG_FILE.parent
    merged = {}
    for path in sorted(catalog_dir.glob("*.json")):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        for source, translation in fragment.items():
            assert source not in merged or merged[source] == translation, source
            merged[source] = translation


def test_dynamic_and_scientific_values_are_not_translated():
    uncertainty_source = (WIZARD_DIR / "uncertainty.py").read_text(encoding="utf-8")
    export_source = (WIZARD_DIR / "db_export_wizard.py").read_text(encoding="utf-8")
    setup_source = (WIZARD_DIR / "project_setup_wizard.py").read_text(encoding="utf-8")

    # stats_arrays descriptions are fixed UI metadata.  Localizing them does
    # not affect calculations because the selected combobox index still maps
    # directly to the distribution ID.
    assert "[_(ud.description) for ud in uncertainty.choices]" in uncertainty_source
    assert (
        "self.dist = uncertainty.id_dict[self.distribution.currentIndex()]"
        in uncertainty_source
    )
    assert "self.export_option.addItem(exporter_id, exporter_id)" in export_source
    assert "self.versions.addItems(release.list_versions())" in setup_source
    assert "self.models.addItems(release.list_system_models(version))" in setup_source


def test_display_text_is_not_used_as_an_internal_choice():
    for path in WIZARD_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            reads_display_text = any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr in {"text", "currentText"}
                for child in ast.walk(node)
            )
            if not reads_display_text:
                continue
            compared_strings = {
                child.value
                for child in ast.walk(node)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            # Choices use indexes, button IDs, fields, itemData, or other stable
            # technical IDs; translated labels never determine behavior.
            assert not compared_strings
