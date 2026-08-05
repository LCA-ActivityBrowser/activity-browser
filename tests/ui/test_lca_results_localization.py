import ast
import json
import re
import string
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT_FILES = (
    ROOT / "activity_browser" / "layouts" / "tabs" / "LCA_results_tabs.py",
    ROOT / "activity_browser" / "layouts" / "tabs" / "LCA_results_tab.py",
)
CATALOG_DIR = ROOT / "activity_browser" / "translations" / "zh_CN"
RESULTS_CATALOG = CATALOG_DIR / "results.json"


def literal_string(node):
    try:
        value = ast.literal_eval(node)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, str) else None


def is_translation_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_"
    )


def static_translation_sources(tree):
    sources = set()
    for node in ast.walk(tree):
        if is_translation_call(node) and node.args:
            source = literal_string(node.args[0])
            if source is not None:
                sources.add(source)
    return sources


def test_results_catalog_covers_every_static_translation_and_aggregation_label():
    catalog = json.loads(RESULTS_CATALOG.read_text(encoding="utf-8"))
    sources = set()
    for path in RESULT_FILES:
        sources.update(static_translation_sources(ast.parse(path.read_text())))

    # Aggregation labels are translated from stable dataframe field IDs at
    # runtime, so their source values cannot be discovered as `_` literals.
    sources.update(
        {
            "none",
            "reference product",
            "name",
            "location",
            "unit",
            "database",
            "categories",
            "type",
        }
    )
    assert not sources.difference(catalog)


def test_results_catalog_has_no_conflicts_and_preserves_placeholders_and_links():
    merged = {}
    formatter = string.Formatter()
    for path in sorted(CATALOG_DIR.glob("*.json")):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        for source, translation in fragment.items():
            assert source not in merged or merged[source] == translation
            merged[source] = translation

    catalog = json.loads(RESULTS_CATALOG.read_text(encoding="utf-8"))
    for source, translation in catalog.items():
        source_fields = {name for _, name, _, _ in formatter.parse(source) if name}
        translated_fields = {
            name for _, name, _, _ in formatter.parse(translation) if name
        }
        assert source_fields == translated_fields
        if source.startswith("<h4>"):
            assert re.findall(r'href="([^"]+)"', source) == re.findall(
                r'href="([^"]+)"', translation
            )

    assert catalog["{name}[Scenarios]"].format(name="ecoinvent 数据") == (
        "ecoinvent 数据[情景]"
    )


def test_fixed_widget_text_is_always_translated():
    constructors = {
        "QLabel",
        "QCheckBox",
        "QRadioButton",
        "QPushButton",
        "QGroupBox",
        "header",
        "get_header_layout",
        "get_header_layout_w_help",
    }
    format_only_labels = {".png", ".svg", ".csv"}

    for path in RESULT_FILES:
        tree = ast.parse(path.read_text())
        assert not any(
            isinstance(node, ast.Name)
            and node.id == "_"
            and isinstance(node.ctx, (ast.Store, ast.Del))
            for node in ast.walk(tree)
        ), f"The translation function is shadowed in {path}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in constructors and node.args:
                    source = literal_string(node.args[0])
                    if source and source not in format_only_labels:
                        raise AssertionError(
                            f"Untranslated {node.func.id} text at {path}:{node.lineno}: "
                            f"{source!r}"
                        )
                elif node.func.id == "QMessageBox" and len(node.args) >= 2:
                    assert literal_string(node.args[1]) is None, (
                        path,
                        node.lineno,
                        literal_string(node.args[1]),
                    )

            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue

            method = node.func.attr
            if method == "setToolTip" and node.args:
                assert literal_string(node.args[0]) is None, (
                    path,
                    node.lineno,
                    literal_string(node.args[0]),
                )
            elif method == "addAction" and len(node.args) >= 2:
                assert literal_string(node.args[1]) is None, (
                    path,
                    node.lineno,
                    literal_string(node.args[1]),
                )
            elif method == "getSaveFileName":
                for keyword in node.keywords:
                    if keyword.arg in {"caption", "filter"}:
                        assert literal_string(keyword.value) is None, (
                            path,
                            node.lineno,
                            keyword.arg,
                        )
            elif method in {"warning", "information", "critical"}:
                if len(node.args) >= 2:
                    assert literal_string(node.args[1]) is None, (
                        path,
                        node.lineno,
                        literal_string(node.args[1]),
                    )

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Attribute) and target.attr in {
                "explain_text",
                "tab_text",
            }:
                assert is_translation_call(node.value), (path, node.lineno, target.attr)

        get_unit = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "get_unit"
            ),
            None,
        )
        if get_unit is not None:
            returned_literals = {
                literal_string(node.value)
                for node in ast.walk(get_unit)
                if isinstance(node, ast.Return)
            }
            assert {
                "relative share",
                "units of each impact category",
            }.issubset(returned_literals)
            assert not any(
                is_translation_call(node) for node in ast.walk(get_unit)
            )


def test_scientific_data_and_internal_result_ids_are_not_translated():
    tabs_source = RESULT_FILES[0].read_text()
    container_source = RESULT_FILES[1].read_text()

    # Dynamic scientific values continue to be read verbatim from their data
    # comboboxes and dictionaries.
    assert "self.parent.method_dict[self.combobox_menu.method.currentText()]" in (
        tabs_source
    )
    assert "functional_unit = self.combobox_menu.func.currentText()" in tabs_source
    assert "return bc.unit_of_method(method)" in tabs_source
    assert 'data = {"Score": score}' in tabs_source
    assert 'data["Range"] = sum(_range)' in tabs_source
    assert 'score_and_rest[col].extend(["Score", "Rest (+)", "Rest (-)"])' in (
        tabs_source
    )
    assert '[_(' not in tabs_source.split("score_and_rest[col].extend", 1)[1].split(
        ")", 1
    )[0]
    assert '["reference product", "name", "location", "unit"]' in tabs_source

    # Raw exception text is retained; only fixed titles and guidance translate.
    assert '_("Could not perform Monte Carlo simulation"), str(e)' in tabs_source
    assert '_("Could not perform GSA"), str(message) + message_addition' in tabs_source
    assert '_("Calculation problem"),\n                str(initial)' in container_source

    # Internal calculation type and dictionary keys retain their stable values;
    # only the separate tab label gets the localized scenario suffix.
    assert 'calculation_type == "scenario"' in container_source
    assert 'internal_name = "{}[Scenarios]".format(cs_name)' in container_source
    assert "self.tabs[internal_name] = new_tab" in container_source
    assert "self.addTab(new_tab, display_name)" in container_source
    assert 'signals.show_tab.emit("LCA results")' in container_source


def test_result_values_translate_only_on_display_copies_not_in_exports():
    model_source = (
        ROOT
        / "activity_browser"
        / "ui"
        / "tables"
        / "models"
        / "lca_results.py"
    ).read_text(encoding="utf-8")
    base_source = (
        ROOT / "activity_browser" / "ui" / "tables" / "models" / "base.py"
    ).read_text(encoding="utf-8")
    figure_source = (
        ROOT / "activity_browser" / "ui" / "figures.py"
    ).read_text(encoding="utf-8")

    for value in (
        '"Score"',
        '"Rest (+)"',
        '"Rest (-)"',
        '"relative share"',
        '"units of each impact category"',
    ):
        assert value in model_source

    # The model translates selected fixed values only after reading them for a
    # display/tooltip role.  Export methods continue to use `_dataframe` raw.
    assert "value in self.TRANSLATABLE_VALUES" in base_source
    assert "value = _(value)" in base_source
    for method_call in (
        "self._dataframe.iloc[rows, columns].to_clipboard",
        "self._dataframe.to_csv(path)",
        "self._dataframe.to_excel(excel_writer=path)",
    ):
        assert method_call in base_source

    # Plot labels are prepared on separate dataframes and only for the
    # recognized built-in prefix, not for a later data row with the same text.
    assert "def prepare_contribution_plot_dataframe" in figure_source
    assert "def prepare_lca_results_plot_dataframe" in figure_source
    assert "source.select_dtypes(include=np.number).copy()" in figure_source
    assert "fixed_prefix" in figure_source
    assert "is_fixed = position < fixed_display_rows" in figure_source
    assert "if translate_unit else unit" in figure_source


def test_calculation_tab_label_localizes_only_the_scenario_suffix():
    source = RESULT_FILES[1].read_text()
    tree = ast.parse(source)
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "calculation_tab_label"
    )
    module = ast.fix_missing_locations(ast.Module(body=[helper], type_ignores=[]))
    catalog = json.loads(RESULTS_CATALOG.read_text(encoding="utf-8"))
    namespace = {
        "_": lambda value, **kwargs: catalog.get(value, value).format(**kwargs)
    }
    exec(compile(module, str(RESULT_FILES[1]), "exec"), namespace)

    label = namespace["calculation_tab_label"]
    scientific_name = "market for electricity | CN | 千瓦时"
    assert label(scientific_name, "simple") == scientific_name
    assert label(scientific_name, "scenario") == scientific_name + "[情景]"
