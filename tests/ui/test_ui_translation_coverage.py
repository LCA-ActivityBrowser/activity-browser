import ast
import json
import re
from collections import Counter
from pathlib import Path
from string import Formatter


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (
    ROOT / "activity_browser" / "layouts",
    ROOT / "activity_browser" / "ui",
)
EXTRA_SOURCE_PATHS = (ROOT / "activity_browser" / "settings.py",)
CATALOG_DIR = ROOT / "activity_browser" / "translations" / "zh_CN"

ENGLISH_WORD = re.compile(r"[A-Za-z]{2,}")

# These strings are intentionally displayed verbatim.  The first group is a
# product name; the second consists of file-format labels and button symbols;
# the third contains scientific/database identifiers or data placeholders.
BRAND_LITERALS = {
    "Activity Browser",
    "Activity Browser - {}",
}
FORMAT_LITERALS = {
    ".csv",
    ".png",
    ".svg",
    "PNG (*.png)",
    "SVG (*.svg)",
}
DATA_LITERALS = {
    "Biosphere3",
    "Europe without Switzerland",
    "Forwast",
    "RER",
    "RoW",
    "nan",
}
DIRECT_LITERAL_WHITELIST = BRAND_LITERALS | FORMAT_LITERALS | DATA_LITERALS

TEXT_CONSTRUCTORS = {
    "QAction",
    "QCheckBox",
    "QCommandLinkButton",
    "QDockWidget",
    "QGroupBox",
    "QLabel",
    "QLineEdit",
    "QMenu",
    "QProgressDialog",
    "QPushButton",
    "QRadioButton",
    "QStandardItem",
    "QTableWidgetItem",
    "QTreeWidgetItem",
    "QListWidgetItem",
    "QToolButton",
}
TEXT_METHODS = {
    "addAction",
    "addItem",
    "addItems",
    "addMenu",
    "addTab",
    "get_header_layout",
    "get_header_layout_w_help",
    "header",
    "insertItem",
    "insertTab",
    "setAccessibleDescription",
    "setAccessibleName",
    "setButtonText",
    "setDescription",
    "setDetailedText",
    "setFormat",
    "setHeaderLabels",
    "setHorizontalHeaderLabels",
    "setIconText",
    "setInformativeText",
    "setItemText",
    "setLabelText",
    "setNameFilter",
    "setNameFilters",
    "setPlaceholderText",
    "setPlainText",
    "setPrefix",
    "setStatusTip",
    "setSuffix",
    "setSubTitle",
    "setTabText",
    "setText",
    "setTitle",
    "setToolTip",
    "setVerticalHeaderLabels",
    "setWhatsThis",
    "setWindowTitle",
    "setHtml",
    "setMarkdown",
    "showMessage",
}
MESSAGE_METHODS = {"about", "critical", "information", "question", "warning"}
FILE_DIALOG_METHODS = {
    "getExistingDirectory",
    "getOpenFileName",
    "getOpenFileNames",
    "getSaveFileName",
}
INPUT_DIALOG_METHODS = {"getDouble", "getInt", "getItem", "getText"}
PLOT_FIRST_ARGUMENT_METHODS = {
    "annotate",
    "set_title",
    "set_xlabel",
    "set_ylabel",
    "suptitle",
}
PLOT_LABEL_METHODS = {"axhline", "axvline", "bar", "barh", "hist", "plot"}

UPSTREAM_UNCERTAINTY_DESCRIPTIONS = {
    "Bernoulli uncertainty",
    "Beta PERT uncertainty",
    "Beta uncertainty",
    "Discrete uniform uncertainty",
    "Gamma uncertainty",
    "Generalized extreme value uncertainty",
    "Lognormal uncertainty",
    "No uncertainty",
    "Normal uncertainty",
    "Student's T uncertainty",
    "Triangular uncertainty",
    "Undefined or unknown uncertainty",
    # Older supported stats_arrays releases used this shorter description.
    "Undefined uncertainty",
    "Uniform uncertainty",
    "Weibull uncertainty",
}

INDIRECT_UI_SOURCES = UPSTREAM_UNCERTAINTY_DESCRIPTIONS | {
    # These labels are deliberately stored as raw IDs or source-library
    # metadata, then translated only where Qt displays them.
    "No classification",
    "All Files (*.*)",
    "CSV (*.csv);; All Files (*.*)",
    "TSV (*.tsv);; All Files (*.*)",
    "Excel (*.xlsx);; All Files (*.*)",
}

# These declared columns are intentionally not localized. ``cf`` is hidden and
# stores the characterization-factor object; the ISIC text is the official
# scientific classification-system name shown verbatim.
RAW_DECLARED_HEADER_LITERALS = {"cf", "ISIC rev.4 ecoinvent"}


def source_paths():
    return sorted(
        [path for root in SOURCE_ROOTS for path in root.rglob("*.py")]
        + list(EXTRA_SOURCE_PATHS)
    )


def qualified_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def is_translation_call(node):
    return (
        isinstance(node, ast.Call)
        and qualified_name(node.func).rsplit(".", 1)[-1] == "_"
    )


def direct_strings(node):
    """Return fixed strings that reach a UI sink without passing through `_`."""

    if is_translation_call(node):
        return []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [
            "".join(
                value.value
                if isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                else "{}"
                for value in node.values
            )
        ]
    if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        return [value for item in node.elts for value in direct_strings(item)]
    if isinstance(node, ast.IfExp):
        return direct_strings(node.body) + direct_strings(node.orelse)
    if isinstance(node, ast.BinOp):
        return direct_strings(node.left) + direct_strings(node.right)
    return []


def text_arguments(call):
    name = qualified_name(call.func).rsplit(".", 1)[-1]
    qualified = qualified_name(call.func)

    if name in TEXT_CONSTRUCTORS or name in TEXT_METHODS:
        return list(call.args) + [
            keyword.value
            for keyword in call.keywords
            if keyword.arg in {"label", "text", "title"}
        ]
    if name == "QMessageBox":
        return list(call.args[1:3])
    if name in MESSAGE_METHODS and "QMessageBox" in qualified:
        return list(call.args[1:3])
    if name in FILE_DIALOG_METHODS:
        positional = [
            argument
            for index, argument in enumerate(call.args)
            if index in {1, 3}
        ]
        keyword = [
            item.value
            for item in call.keywords
            if item.arg in {"caption", "filter", "selectedFilter"}
        ]
        return positional + keyword
    if name in INPUT_DIALOG_METHODS and "QInputDialog" in qualified:
        return list(call.args[1:3])
    if name in PLOT_FIRST_ARGUMENT_METHODS:
        return list(call.args[:1])
    if name == "text":
        # matplotlib Axes.text(x, y, text, ...)
        return list(call.args[2:3])
    if name in PLOT_LABEL_METHODS:
        return [item.value for item in call.keywords if item.arg == "label"]
    return []


def merged_catalog():
    merged = {}
    origins = {}
    conflicts = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        for source, translation in fragment.items():
            if source in merged and merged[source] != translation:
                conflicts.append((source, origins[source], path.name))
            merged[source] = translation
            origins[source] = path.name
    return merged, conflicts


def format_signature(value):
    return Counter(
        (field_name, format_spec, conversion)
        for _, field_name, format_spec, conversion in Formatter().parse(value)
        if field_name is not None
    )


def static_translation_sources(tree):
    sources = set()
    for node in ast.walk(tree):
        if not is_translation_call(node) or not node.args:
            continue
        try:
            source = ast.literal_eval(node.args[0])
        except (TypeError, ValueError):
            continue
        if isinstance(source, str):
            sources.add(source)
    return sources


def test_known_ui_text_entries_do_not_receive_fixed_untranslated_english():
    untranslated = []
    for path in source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for argument in text_arguments(node):
                for value in direct_strings(argument):
                    if (
                        ENGLISH_WORD.search(value)
                        and value not in DIRECT_LITERAL_WHITELIST
                    ):
                        untranslated.append(
                            (
                                str(path.relative_to(ROOT)),
                                node.lineno,
                                qualified_name(node.func),
                                value,
                            )
                        )
    assert untranslated == []


class TranslationScopeVisitor(ast.NodeVisitor):
    """Find gettext calls and assignments to `_` in one Python function scope."""

    def __init__(self, root):
        self.root = root
        self.calls = []
        self.stores = []

    def visit_FunctionDef(self, node):
        if node is self.root:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if node is self.root:
            self.generic_visit(node)

    def visit_Lambda(self, node):
        return

    def _visit_comprehension(self, node):
        # Comprehension targets have their own scope in Python 3.  Expressions
        # and iterable sources can still load names from the surrounding scope.
        if hasattr(node, "elt"):
            self.visit(node.elt)
        else:
            self.visit(node.key)
            self.visit(node.value)
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_DictComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension

    def visit_Name(self, node):
        if node.id == "_" and isinstance(node.ctx, (ast.Del, ast.Store)):
            self.stores.append(node.lineno)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "_":
            self.calls.append(node.lineno)
        self.generic_visit(node)


def test_gettext_name_is_not_shadowed_in_the_same_function_scope():
    shadowing = []
    for path in source_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            visitor = TranslationScopeVisitor(function)
            visitor.visit(function)
            if visitor.calls and visitor.stores:
                shadowing.append(
                    (
                        str(path.relative_to(ROOT)),
                        function.name,
                        visitor.stores,
                        visitor.calls,
                    )
                )
    assert shadowing == []


def test_layout_and_ui_translation_sources_are_catalogued_safely():
    catalog, conflicts = merged_catalog()
    assert conflicts == []

    sources = set()
    for path in source_paths():
        sources.update(
            static_translation_sources(ast.parse(path.read_text(encoding="utf-8")))
        )
    sources.update(INDIRECT_UI_SOURCES)
    assert sources.difference(catalog) == set()

    for source, translation in catalog.items():
        assert format_signature(source) == format_signature(translation), source
        assert re.findall(r'href="([^"]+)"', source) == re.findall(
            r'href="([^"]+)"', translation
        ), source


def enclosing_display_role_branch(node, parents, function):
    current = node
    while current in parents and parents[current] is not function:
        current = parents[current]
        if isinstance(current, ast.If):
            if any(
                isinstance(part, ast.Attribute) and part.attr == "DisplayRole"
                for part in ast.walk(current.test)
            ):
                return True
    return False


def assignment_names(node):
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {
        target.id
        for target in targets
        if isinstance(target, ast.Name)
    }


def test_model_headers_are_raw_in_data_and_translated_only_for_display_role():
    model_root = ROOT / "activity_browser" / "ui" / "tables" / "models"
    catalog, _conflicts = merged_catalog()
    translated_header_functions = 0
    data_declarations = {
        "COLUMNS",
        "HEADERS",
        "RESULT_METADATA_HEADERS",
        "TRANSLATABLE_HEADERS",
        "TRANSLATABLE_VALUES",
        "UNCERTAINTY",
    }

    for path in sorted(model_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and (
                assignment_names(node) & data_declarations
            ):
                assert not any(
                    is_translation_call(part) for part in ast.walk(node.value)
                ), (path, node.lineno)
                declared_literals = {
                    part.value
                    for part in ast.walk(node.value)
                    if isinstance(part, ast.Constant)
                    and isinstance(part.value, str)
                }
                assert declared_literals.difference(
                    catalog, RAW_DECLARED_HEADER_LITERALS
                ) == set(), (path, node.lineno)

            if not isinstance(node, ast.FunctionDef) or node.name != "headerData":
                continue
            calls = [part for part in ast.walk(node) if is_translation_call(part)]
            if calls:
                translated_header_functions += 1
            assert all(
                enclosing_display_role_branch(call, parents, node) for call in calls
            ), (path, node.lineno)

    assert translated_header_functions >= 2

    base_path = model_root / "base.py"
    base_tree = ast.parse(base_path.read_text(encoding="utf-8"))
    pandas_model = next(
        node
        for node in base_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PandasModel"
    )
    export_methods = {
        node.name: node
        for node in pandas_model.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"to_clipboard", "to_csv", "to_excel"}
    }
    assert set(export_methods) == {"to_clipboard", "to_csv", "to_excel"}
    assert not any(
        is_translation_call(part)
        for method in export_methods.values()
        for part in ast.walk(method)
    )

    base_source = base_path.read_text(encoding="utf-8")
    inventory_view_source = (
        ROOT / "activity_browser" / "ui" / "tables" / "inventory.py"
    ).read_text(encoding="utf-8")
    assert "role in (Qt.DisplayRole, Qt.UserRole)" in base_source
    assert ".data(QtCore.Qt.UserRole)" in inventory_view_source


def test_humanized_dates_follow_the_interface_language():
    base_path = (
        ROOT / "activity_browser" / "ui" / "tables" / "models" / "base.py"
    )
    tree = ast.parse(base_path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "humanize"
    ]
    assert len(calls) == 1

    locale_keywords = [
        keyword.value for keyword in calls[0].keywords if keyword.arg == "locale"
    ]
    assert len(locale_keywords) == 1
    locale_expression = locale_keywords[0]
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "current_language"
        for node in ast.walk(locale_expression)
    )
    assert {
        node.func.attr
        for node in ast.walk(locale_expression)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } >= {"replace", "lower"}


def test_display_labels_are_not_reused_as_table_logic_keys():
    impact_path = (
        ROOT / "activity_browser" / "ui" / "tables" / "impact_categories.py"
    )
    impact_tree = ast.parse(impact_path.read_text(encoding="utf-8"))
    cf_table = next(
        node
        for node in impact_tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "MethodCharacterizationFactorsTable"
    )
    cell_edited = next(
        node
        for node in cf_table.body
        if isinstance(node, ast.FunctionDef) and node.name == "cell_edited"
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "headerData"
        for node in ast.walk(cell_edited)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "index"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "HEADERS"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "Amount"
        for node in ast.walk(cell_edited)
    )

    views_source = (
        ROOT / "activity_browser" / "ui" / "tables" / "views.py"
    ).read_text(encoding="utf-8")
    dialog_source = (
        ROOT / "activity_browser" / "ui" / "widgets" / "dialog.py"
    ).read_text(encoding="utf-8")
    assert "column_names = self.model.filterable_columns" in views_source
    assert "column_labels=column_labels" in views_source
    assert "column_label=column_label" in views_source
    assert "tab_id = self.col_id_2_tab_id[selected_column]" in dialog_source
    assert "self.tabs[tab_id].filter_rows" in dialog_source

    # Plot preparation must also avoid label-based dropping, which would remove
    # every user row with a reserved-looking name.
    figures_source = (ROOT / "activity_browser" / "ui" / "figures.py").read_text(
        encoding="utf-8"
    )
    assert '.drop("Score"' not in figures_source
    assert "fixed_rest_positions" in figures_source
