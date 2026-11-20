import ast
import json
from pathlib import Path
from string import Formatter


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "activity_browser"
CATALOG_DIR = PACKAGE / "translations" / "zh_CN"
SOURCE_PATHS = sorted((PACKAGE / "bwutils").rglob("*.py")) + sorted(
    (PACKAGE / "controllers").rglob("*.py")
) + [PACKAGE / "utils.py"]


def source_trees():
    return {
        path: ast.parse(path.read_text(encoding="utf-8")) for path in SOURCE_PATHS
    }


def merged_catalog():
    translations = {}
    origins = {}
    for path in sorted(CATALOG_DIR.glob("*.json")):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        for source, translation in fragment.items():
            if source in translations:
                assert translations[source] == translation, (
                    source,
                    origins[source],
                    path,
                )
            translations[source] = translation
            origins[source] = path
    return translations


def callee_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def is_translation_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_"
    )


def contains_translation_call(node):
    return any(is_translation_call(candidate) for candidate in ast.walk(node))


def literal_translation_sources(trees):
    sources = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if not (is_translation_call(node) and node.args):
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


def assignments_in(function):
    assignments = {}
    for node in ast.walk(function):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            for target in targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = value
    return assignments


def translated_expression(node, assignments):
    if contains_translation_call(node):
        return True
    return (
        isinstance(node, ast.Name)
        and node.id in assignments
        and contains_translation_call(assignments[node.id])
    )


def test_backend_ui_translation_calls_are_catalogued_with_matching_fields():
    trees = source_trees()
    catalog = merged_catalog()
    sources = literal_translation_sources(trees)

    assert sources <= set(catalog)
    for source in sources:
        assert format_fields(source) == format_fields(catalog[source]), source


def test_translation_helper_is_not_shadowed_inside_translating_functions():
    offenders = []
    for path, tree in source_trees().items():
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            has_translation = any(is_translation_call(node) for node in ast.walk(function))
            shadows_translation = any(
                isinstance(node, ast.Name)
                and node.id == "_"
                and isinstance(node.ctx, ast.Store)
                for node in ast.walk(function)
            )
            if has_translation and shadows_translation:
                offenders.append((path, function.lineno, function.name))

    assert offenders == []


def test_abpopup_callers_translate_titles_messages_and_buttons():
    popup_calls = []
    untranslated = []
    for path, tree in source_trees().items():
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            assignments = assignments_in(function)
            for node in ast.walk(function):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"abCritical", "abQuestion", "abWarning"}
                ):
                    continue
                popup_calls.append((path, node.lineno))
                if len(node.args) < 2:
                    untranslated.append((path, node.lineno, "missing title/message"))
                    continue
                for role, argument in zip(("title", "message"), node.args[:2]):
                    if not translated_expression(argument, assignments):
                        untranslated.append((path, node.lineno, role))
                for argument in node.args[2:]:
                    if (
                        isinstance(argument, ast.Call)
                        and callee_name(argument) == "QPushButton"
                        and argument.args
                        and not translated_expression(argument.args[0], assignments)
                    ):
                        untranslated.append((path, node.lineno, "button"))

    assert popup_calls
    assert untranslated == []


def test_fixed_backend_qt_text_is_not_left_as_a_direct_literal():
    text_constructors = {"QCheckBox", "QGroupBox", "QLabel", "QPushButton"}
    text_methods = {
        "setInformativeText": 0,
        "setPlaceholderText": 0,
        "setText": 0,
        "setToolTip": 0,
        "setWindowTitle": 0,
    }
    untranslated = []

    for path, tree in source_trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = callee_name(node)
            arguments = []
            if name in text_constructors and node.args:
                arguments.append(node.args[0])
            elif name in text_methods and len(node.args) > text_methods[name]:
                arguments.append(node.args[text_methods[name]])
            elif name == "BW2CalcError":
                arguments.extend(node.args[:2])

            if name == "getSaveFileName":
                arguments.extend(
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg in {"caption", "filter", "selectedFilter"}
                )

            for argument in arguments:
                if isinstance(argument, (ast.Constant, ast.JoinedStr)):
                    value = getattr(argument, "value", "formatted string")
                    if value:
                        untranslated.append((path, node.lineno, value))

    assert untranslated == []


def test_scientific_fields_and_dynamic_exception_details_stay_untranslated():
    catalog = merged_catalog()
    data_fields = {
        "file",
        "flow type",
        "from activity name",
        "from database",
        "from key",
        "to activity name",
        "to database",
        "to key",
    }
    assert data_fields.isdisjoint(catalog)

    path = PACKAGE / "bwutils" / "superstructure" / "file_dialogs.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    model = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ProblemDataModel"
    )
    header = next(
        node
        for node in model.body
        if isinstance(node, ast.FunctionDef) and node.name == "headerData"
    )
    assert "return str(self.columns[section])" in ast.unparse(header)
    assert not contains_translation_call(header)

    calculations = (PACKAGE / "bwutils" / "calculations.py").read_text(
        encoding="utf-8"
    )
    assert "str(e)" in calculations
    assert "_(str(e))" not in calculations
