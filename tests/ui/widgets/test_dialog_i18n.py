import ast
import json
from pathlib import Path
from string import Formatter


ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = ROOT / "activity_browser" / "ui" / "widgets" / "dialog.py"
CATALOG_PATH = (
    ROOT / "activity_browser" / "translations" / "zh_CN" / "dialogs.json"
)


def source_tree():
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def literal_translation_sources(tree):
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
        except (TypeError, ValueError):
            continue
        if isinstance(source, str):
            sources.add(source)
    return sources


def format_fields(value):
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name is not None
    }


def test_dialog_catalog_covers_every_literal_translation_call():
    assert set(catalog()) == literal_translation_sources(source_tree())


def test_dialog_catalog_preserves_placeholders_and_scientific_data():
    translations = catalog()
    for source, translation in translations.items():
        assert format_fields(source) == format_fields(translation), source

    # These are location/data identifiers and must not become translation keys.
    for data_name in ("RoW", "RER", "Europe without Switzerland", "biosphere3"):
        assert data_name not in translations

    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert 'QtWidgets.QCheckBox("RoW")' in source
    assert 'QtWidgets.QCheckBox("RER")' in source
    assert 'QtWidgets.QCheckBox("Europe without Switzerland")' in source
    assert "self.options.addItems(sort_semantic_versions(__ei_versions__))" in source
    assert 'QtWidgets.QPushButton(act.as_dict()["name"])' in source


def test_dialog_display_labels_do_not_replace_stable_item_data():
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "self.field_separator.addItem(label, separator)" in source
    assert "self.filter_type_box.addItem(label, filter_id)" in source
    assert "selected_type = self.filter_type_box.currentData()" in source
    assert 'self.AND.setProperty("filter_mode", FILTER_MODE_AND)' in source
    assert 'self.OR.setProperty("filter_mode", FILTER_MODE_OR)' in source
    assert 'checkedButton().property("filter_mode")' in source


def test_fixed_dialog_widget_text_is_not_left_as_a_direct_literal():
    tree = source_tree()
    text_constructors = {
        "QCheckBox",
        "QGroupBox",
        "QLabel",
        "QPushButton",
        "QRadioButton",
    }
    text_methods = {
        "setButtonText": 1,
        "setPlaceholderText": 0,
        "setText": 0,
        "setToolTip": 0,
        "setWindowTitle": 0,
    }
    allowed_data_literals = {"RoW", "RER", "Europe without Switzerland"}
    untranslated = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        function_name = node.func.attr
        candidate_arguments = []

        if function_name in text_constructors and node.args:
            candidate_arguments.append(node.args[0])
        elif function_name in text_methods and len(node.args) > text_methods[function_name]:
            candidate_arguments.append(node.args[text_methods[function_name]])

        if function_name == "getOpenFileName":
            candidate_arguments.extend(
                keyword.value
                for keyword in node.keywords
                if keyword.arg in {"caption", "filter", "selectedFilter"}
            )

        for argument in candidate_arguments:
            if (
                isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
                and argument.value
                and argument.value not in allowed_data_literals
            ):
                untranslated.append((node.lineno, argument.value))

    assert untranslated == []
