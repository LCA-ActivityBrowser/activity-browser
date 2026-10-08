import ast
import json
import string
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ACTIONS_DIR = ROOT / "activity_browser" / "actions"
ACTION_FILES = tuple(sorted(ACTIONS_DIR.rglob("*.py")))
CATALOG_FILE = ROOT / "activity_browser" / "translations" / "zh_CN" / "actions.json"


def _catalog():
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def _literal_value(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _class_ui_sources(tree):
    sources = set()
    for class_node in (
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    ):
        for statement in class_node.body:
            if isinstance(statement, ast.Assign):
                targets = statement.targets
                value_node = statement.value
            elif isinstance(statement, ast.AnnAssign):
                targets = (statement.target,)
                value_node = statement.value
            else:
                continue
            for target in targets:
                if not (
                    isinstance(target, ast.Name)
                    and target.id in {"text", "tool_tip", "tooltip"}
                ):
                    continue
                value = _literal_value(value_node)
                if isinstance(value, str) and value:
                    sources.add(value)
    return sources


def _literal_gettext_sources(tree):
    sources = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_"
            and node.args
        ):
            continue
        value = _literal_value(node.args[0])
        if isinstance(value, str):
            sources.add(value)
    return sources


def _module_ui_collections(tree):
    """Collect fixed UI source collections translated later in a loop."""

    sources = set()
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id.endswith("_STRINGS")
            for target in statement.targets
        ):
            continue
        value = _literal_value(statement.value)
        if isinstance(value, (tuple, list)):
            sources.update(item for item in value if isinstance(item, str))
    return sources


def test_action_class_and_direct_ui_sources_are_in_catalog():
    sources = set()
    class_sources = set()
    for path in ACTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        class_sources.update(_class_ui_sources(tree))
        sources.update(_literal_gettext_sources(tree))
        sources.update(_module_ui_collections(tree))
    sources.update(class_sources)

    assert len(class_sources) >= 60
    assert sources <= _catalog().keys()


def _untranslated_literals(node):
    """Return alphabetic literals which are not inside a gettext call."""

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "_":
            return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value] if any(char.isalpha() for char in node.value) else []
    literals = []
    for child in ast.iter_child_nodes(node):
        literals.extend(_untranslated_literals(child))
    return literals


def _ui_text_arguments(call):
    if isinstance(call.func, ast.Attribute):
        name = call.func.attr
    elif isinstance(call.func, ast.Name):
        name = call.func.id
    else:
        return []

    if name in {"warning", "information", "critical", "question", "getText", "getItem"}:
        return call.args[1:3]
    if name in {"getOpenFileName", "getSaveFileName"}:
        return [
            keyword.value
            for keyword in call.keywords
            if keyword.arg in {"caption", "filter"}
        ]
    if name == "QProgressDialog":
        return [
            keyword.value for keyword in call.keywords if keyword.arg == "labelText"
        ]
    if name in {
        "showMessage",
        "setWindowTitle",
        "setLabelText",
        "setTitle",
        "setSubTitle",
        "setToolTip",
        "setPlaceholderText",
    }:
        return call.args[:1]
    if name in {"QGroupBox", "QLabel", "QRadioButton"}:
        return call.args[:1]
    if name == "QPushButton":
        return call.args[1:2] if len(call.args) > 1 else call.args[:1]
    if name == "get_combined_name":
        # Parent is first; title and field label are UI. The remaining suffix
        # becomes part of the new scientific method name and stays unchanged.
        return call.args[1:3]
    return []


def test_direct_ui_literals_are_translated():
    for path in ACTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }

        def enclosing_function(node):
            while node in parents:
                node = parents[node]
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return node
            return tree

        assignments_by_scope = {}

        def assignments_for(scope):
            if scope in assignments_by_scope:
                return assignments_by_scope[scope]
            assignments = {}
            for node in ast.walk(scope):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            assignments.setdefault(target.id, []).append(node.value)
                elif isinstance(node, ast.AugAssign) and isinstance(
                    node.target, ast.Name
                ):
                    assignments.setdefault(node.target.id, []).append(node.value)
            assignments_by_scope[scope] = assignments
            return assignments

        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            assignments = assignments_for(enclosing_function(call))
            for argument in _ui_text_arguments(call):
                values = (
                    assignments.get(argument.id, ())
                    if isinstance(argument, ast.Name)
                    else (argument,)
                )
                for value in values:
                    assert not _untranslated_literals(value), (
                        path,
                        call.lineno,
                        _untranslated_literals(value),
                    )


def test_gettext_is_not_shadowed_by_dialog_return_values():
    for path in ACTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        uses_gettext = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_"
            for node in ast.walk(tree)
        )
        if not uses_gettext:
            continue
        shadowing = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node.id == "_"
        ]
        assert not shadowing, (path, shadowing)


def test_action_translation_placeholders_are_named_and_match():
    formatter = string.Formatter()

    def fields(value):
        return sorted(
            field for _, field, _, _ in formatter.parse(value) if field is not None
        )

    for source, translation in _catalog().items():
        source_fields = fields(source)
        assert all(field and not field.isdigit() for field in source_fields), source
        assert source_fields == fields(translation), source

    for path in ACTION_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_"
                and node.args
            ):
                continue
            source = _literal_value(node.args[0])
            if not isinstance(source, str):
                continue
            expected = set(fields(source))
            supplied = {keyword.arg for keyword in node.keywords if keyword.arg}
            assert expected == supplied, (path, node.lineno, expected, supplied)
