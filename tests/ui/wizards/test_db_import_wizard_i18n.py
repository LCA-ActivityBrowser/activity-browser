import ast
import json
from pathlib import Path
from string import Formatter


ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = ROOT / "activity_browser" / "ui" / "wizards" / "db_import_wizard.py"
CATALOG_PATH = (
    ROOT
    / "activity_browser"
    / "translations"
    / "zh_CN"
    / "wizard_import.json"
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
        except (ValueError, TypeError):
            continue
        if isinstance(source, str):
            sources.add(source)
    return sources


def option_labels(tree):
    labels = set()
    page_names = {"ImportTypePage", "RemoteImportPage", "LocalImportPage"}
    for class_node in (
        node for node in tree.body if isinstance(node, ast.ClassDef)
    ):
        if class_node.name not in page_names:
            continue
        options_node = next(
            node
            for node in class_node.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "OPTIONS"
                for target in node.targets
            )
        )
        labels.update(option.elts[0].value for option in options_node.value.elts)
    # Forwast is a database/proper name and deliberately bypasses translation.
    labels.remove("Forwast")
    return labels


def format_fields(value):
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name is not None
    }


def test_import_wizard_catalog_covers_all_translation_calls():
    tree = source_tree()
    expected = literal_translation_sources(tree) | option_labels(tree)

    assert set(catalog()) == expected


def test_import_wizard_catalog_preserves_format_fields_and_data_names():
    translations = catalog()
    for source, translation in translations.items():
        assert format_fields(source) == format_fields(translation), source

    # Scientific/data identifiers remain source data, not translation keys.
    assert "Forwast" not in translations
    assert "biosphere3" not in translations
    assert "cutoff" not in translations
    assert "consequential" not in translations

    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert 'option[0] if option[1] == "forwast" else _(option[0])' in source
    assert "return self.ecoinvent_version_page.version_combobox.currentText()" in source
    assert "return self.ecoinvent_version_page.system_model_combobox.currentText()" in source


def test_fixed_widget_text_is_not_left_as_direct_string_literals():
    tree = source_tree()
    text_constructors = {"QGroupBox", "QLabel", "QPushButton", "QRadioButton"}
    text_methods = {
        "setButtonText": 1,
        "setPlaceholderText": 0,
        "setSubTitle": 0,
        "setText": 0,
        "setTitle": 0,
        "setWindowTitle": 0,
    }
    untranslated = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        function_name = node.func.attr
        text_arg = None
        if function_name in text_constructors and node.args:
            text_arg = node.args[0]
        elif function_name in text_methods and len(node.args) > text_methods[function_name]:
            text_arg = node.args[text_methods[function_name]]

        if function_name in {"getExistingDirectory", "getOpenFileName"}:
            caption = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "caption"),
                None,
            )
            if caption is None and len(node.args) > 1:
                caption = node.args[1]
            text_arg = caption
            for keyword in node.keywords:
                if (
                    keyword.arg == "filter"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                    and keyword.value.value
                ):
                    untranslated.append((node.lineno, keyword.value.value))

        # QMessageBox titles and messages are the second and third arguments.
        if function_name in {"information", "question", "warning"}:
            for argument in node.args[1:3]:
                if (
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and argument.value
                ):
                    untranslated.append((node.lineno, argument.value))

        if (
            isinstance(text_arg, ast.Constant)
            and isinstance(text_arg.value, str)
            and text_arg.value
            and text_arg.value != "Forwast"
        ):
            untranslated.append((node.lineno, text_arg.value))

    assert untranslated == []
