from types import SimpleNamespace

import pandas as pd
from PySide2.QtCore import QModelIndex, Qt
from PySide2 import QtWidgets
from PySide2.QtGui import QStandardItemModel

from activity_browser.layouts.panels.panel import ABTab, TabId
from activity_browser.layouts.tabs.LCA_results_tabs import (
    CategorisationFilter,
    ContributionTab,
    InventoryTab,
    InventoryType,
)
from activity_browser.ui.tables.models.base import (
    BaseTreeModel,
    FilterMode,
    FilterOperator,
    PandasModel,
    TreeItem,
)
from activity_browser.ui.tables.models.lca_results import (
    ContributionModel,
    InventoryModel,
    LCAResultsModel,
)
from activity_browser.ui.tables.models.lca_setup import CSActivityModel, CSMethodsModel
from activity_browser.ui.tables.delegates.uncertainty import UncertaintyDelegate
from activity_browser.ui.tables.views import ABFilterableDataFrameView
from activity_browser.ui.tables.impact_categories import (
    MethodCharacterizationFactorsTable,
    MethodsTable,
)
from activity_browser.ui.figures import (
    CHINESE_PLOT_FONTS,
    configure_plot_fonts,
    prepare_contribution_plot_dataframe,
    prepare_lca_results_plot_dataframe,
)
from activity_browser.ui.widgets.comparison_switch import ComparisonMode, SwitchComboBox
from activity_browser.ui.widgets.dialog import (
    AndOrRadioButtons,
    FilterManagerDialog,
    NumFilterRow,
    SimpleFilterDialog,
    StrFilterRow,
)


def test_panel_tab_logic_uses_stable_id_and_accepts_legacy_alias(qtbot):
    panel = ABTab()
    tab = QtWidgets.QWidget()
    qtbot.addWidget(panel)

    panel.add_tab(
        tab,
        TabId.GRAPH_EXPLORER,
        "图形浏览器",
        aliases=("Graph Explorer",),
    )

    assert panel.tabText(0) == "图形浏览器"
    assert panel.get_tab_name_from_index(0) == TabId.GRAPH_EXPLORER

    panel.hide_tab(TabId.GRAPH_EXPLORER)
    assert panel.indexOf(tab) == -1

    # Older emitters can still use the historical English label, but the
    # translated display label is never used as the internal key.
    panel.show_tab("Graph Explorer")
    assert panel.indexOf(tab) == 0
    assert panel.tabText(0) == "图形浏览器"


def test_filter_rows_return_item_data_after_labels_are_translated(qtbot):
    filter_types = ABFilterableDataFrameView.FILTER_TYPES

    string_row = StrFilterRow(idx=0, filter_types=filter_types, remove_option=False)
    qtbot.addWidget(string_row)
    string_row.filter_type_box.setItemText(0, "包含")
    string_row.set_state((FilterOperator.CONTAINS, "coal", False))

    assert string_row.filter_type_box.currentText() == "包含"
    assert string_row.get_state == (FilterOperator.CONTAINS, "coal", False)

    numeric_row = NumFilterRow(idx=0, filter_types=filter_types, remove_option=False)
    qtbot.addWidget(numeric_row)
    between_index = numeric_row.filter_ids.index(FilterOperator.BETWEEN)
    numeric_row.filter_type_box.setItemText(between_index, "介于")
    numeric_row.set_state((FilterOperator.BETWEEN, ("1", "2")))

    assert numeric_row.filter_type_box.currentText() == "介于"
    assert numeric_row.filter_query_line0.isHidden() is False
    assert numeric_row.get_state == (FilterOperator.BETWEEN, ("1", "2"))


def test_and_or_mode_does_not_depend_on_radio_button_text(qtbot):
    buttons = AndOrRadioButtons()
    qtbot.addWidget(buttons)

    buttons.AND.setText("并且")
    buttons.OR.setText("或者")
    buttons.set_state(FilterMode.OR)

    assert buttons.get_state == FilterMode.OR


def test_filter_model_uses_stable_operator_and_mode_ids():
    model = PandasModel(
        pd.DataFrame(
            {
                "name": ["hard coal", "wind power", "coal market"],
                "amount": [1.0, 2.0, 3.0],
            }
        )
    )
    model.filterable_columns = {"name": 0, "amount": 1}
    model.different_column_types = {"amount": "num"}
    filters = {
        0: {"filters": [(FilterOperator.CONTAINS, "coal", False)]},
        1: {
            "filters": [(FilterOperator.GREATER_THAN_OR_EQUAL, "2")],
        },
        "mode": FilterMode.AND,
    }

    assert model.get_filter_mask(filters).tolist() == [False, False, True]


def test_comparison_mode_does_not_depend_on_combobox_text(qtbot):
    parent = QtWidgets.QWidget()
    parent.has_scenarios = True
    qtbot.addWidget(parent)
    box = SwitchComboBox(parent)
    box.configure()

    assert [box.itemData(i) for i in range(box.count())] == [
        ComparisonMode.FUNCTIONAL_UNITS,
        ComparisonMode.IMPACT_CATEGORIES,
        ComparisonMode.SCENARIOS,
    ]

    box.setItemText(box.indexes.method, "影响类别")
    box.setCurrentIndex(box.indexes.method)
    assert box.currentText() == "影响类别"
    assert box.current_mode == ComparisonMode.IMPACT_CATEGORIES


def test_lca_aggregation_labels_preserve_dataframe_fields(qtbot, monkeypatch):
    translations = {"none": "不聚合", "location": "地点"}
    monkeypatch.setattr(
        "activity_browser.layouts.tabs.LCA_results_tabs._",
        lambda source: translations.get(source, source),
    )
    box = QtWidgets.QComboBox()
    qtbot.addWidget(box)

    ContributionTab.add_aggregation_items(box, ["none", "location"])

    assert [box.itemText(i) for i in range(box.count())] == ["不聚合", "地点"]
    assert [box.itemData(i) for i in range(box.count())] == ["none", "location"]


def test_inventory_filters_use_combobox_data_and_button_property():
    class Combo:
        def __init__(self, value):
            self.value = value

        def currentData(self):
            return self.value

    holder = SimpleNamespace(
        bio_categorisation_factor_group=Combo(CategorisationFilter.WITH_FACTORS),
        categorisation_filter_with_flows=None,
        categorisation_factor_state=None,
        old_categorisation_factor_state=None,
        update_table=lambda: None,
    )
    InventoryTab.add_categorisation_factor_filter(holder, 0)
    assert holder.categorisation_filter_with_flows is True

    visibility = []
    holder.categorisation_filter_box = SimpleNamespace(
        setVisible=lambda visible: visibility.append(visible)
    )
    translated_button = SimpleNamespace(
        property=lambda name: InventoryType.BIOSPHERE,
        text=lambda: "生物圈流",
    )
    InventoryTab.toggle_categorisation_factor_filter_buttons(
        holder, translated_button
    )
    assert visibility == [True]


def test_contribution_labels_translate_only_in_builtin_rows(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.base._",
        lambda value: {"Score": "得分", "Rest (+)": "其余（正）"}.get(value, value),
    )
    model = ContributionModel()
    source = pd.DataFrame(
        {
            "index": ["Score", "Rest (+)", "Rest (-)", "Score"],
            "unit": ["kg", "kg", "kg", "kg"],
            "result": [4.0, 1.0, -1.0, 2.0],
        }
    )

    model.sync(source, unit="kg")
    label_column = model._dataframe.columns.get_loc("index")
    builtin = model.index(0, label_column)
    user_data = model.index(3, label_column)

    assert model.data(builtin, Qt.DisplayRole) == "得分"
    assert model.data(user_data, Qt.DisplayRole) == "Score"
    assert model.data(builtin, "sorting") == "Score"
    assert model._dataframe.iloc[3, label_column] == "Score"


def test_result_headers_translate_only_program_defined_metadata(monkeypatch):
    translations = {
        "name": "名称",
        "unit": "单位",
        "database": "数据库",
        "code": "代码",
    }
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.base._",
        lambda value: translations.get(value, value),
    )
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.lca_results._",
        lambda value: translations.get(value, value),
    )
    columns = [
        "index",
        "amount",
        "unit",
        "reference product",
        "name",
        "location",
        "database",
        "name",
    ]
    model = LCAResultsModel()
    model.sync(
        pd.DataFrame(
            [["row", 1.0, "kg", "product", "activity", "CN", "db", 4.2]],
            columns=columns,
        )
    )

    assert model.headerData(4, Qt.Horizontal, Qt.DisplayRole) == "名称"
    assert model.headerData(7, Qt.Horizontal, Qt.DisplayRole) == "name"
    assert list(model._dataframe.columns) == columns

    monte_carlo = LCAResultsModel()
    monte_carlo.sync(pd.DataFrame({"name": [1.0]}))
    assert monte_carlo.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "name"

    scientific_schema_collision = LCAResultsModel()
    scientific_schema_collision.sync(
        pd.DataFrame(
            [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]],
            columns=[
                "amount",
                "unit",
                "reference product",
                "name",
                "location",
                "database",
            ],
        )
    )
    assert (
        scientific_schema_collision.headerData(3, Qt.Horizontal, Qt.DisplayRole)
        == "name"
    )

    index_alias_collision = LCAResultsModel()
    index_alias_collision.sync(
        pd.DataFrame(
            [[1.0, 2.0, 3.0]],
            columns=["level_0", "level_1", "amount"],
        )
    )
    assert (
        index_alias_collision.headerData(0, Qt.Horizontal, Qt.DisplayRole)
        == "level_0"
    )

    # Pandas names unnamed MultiIndex fields ``level_0`` and ``level_1``.
    # Only their display headers are made meaningful; exported/raw fields and
    # dynamically named result columns remain unchanged.
    overview_columns = [
        "level_0",
        "level_1",
        "amount",
        "unit",
        "reference product",
        "name",
        "location",
        "database",
        ("method", "category"),
    ]
    overview = LCAResultsModel()
    overview.sync(
        pd.DataFrame(
            [["db", "code", 1.0, "kg", "product", "activity", "CN", "db", 2.0]],
            columns=overview_columns,
        )
    )
    assert overview.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "数据库"
    assert overview.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "代码"
    assert overview.headerData(8, Qt.Horizontal, Qt.DisplayRole) == (
        "method",
        "category",
    )
    assert list(overview._dataframe.columns) == overview_columns


def test_filter_dialogs_use_display_labels_but_keep_raw_column_keys(
    qtbot, monkeypatch
):
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.base._",
        lambda value: {"name": "名称", "unit": "单位"}.get(value, value),
    )
    model = InventoryModel()
    model.sync(
        pd.DataFrame(
            {
                "name": ["flow"],
                "categories": ["air"],
                "type": ["biosphere"],
                "unit": ["kg"],
                "database": ["db"],
                "scientific result": [1.0],
            }
        )
    )

    manager = FilterManagerDialog(
        column_names=model.filterable_columns,
        column_labels={
            column: model.headerData(column, Qt.Horizontal, Qt.DisplayRole)
            for column in model.filterable_columns.values()
        },
        filter_types=ABFilterableDataFrameView.FILTER_TYPES,
    )
    qtbot.addWidget(manager)
    assert manager.tab_widget.tabText(0) == "名称"
    assert manager.tab_widget.tabText(5) == "scientific result"

    simple = SimpleFilterDialog(
        column_name="name",
        column_label=model.headerData(0, Qt.Horizontal, Qt.DisplayRole),
        filter_types=ABFilterableDataFrameView.FILTER_TYPES,
    )
    qtbot.addWidget(simple)
    visible_text = [label.text() for label in simple.findChildren(QtWidgets.QLabel)]
    assert any("名称" in text for text in visible_text)

    # Filtering still addresses the raw dataframe field, never the display label.
    assert model.filterable_columns["name"] == 0
    assert "名称" not in model.filterable_columns


def test_filter_manager_maps_non_contiguous_raw_columns_to_display_tabs(qtbot):
    manager = FilterManagerDialog(
        column_names={"Name": 0, "Amount": 3},
        column_labels={0: "名称", 3: "数值"},
        column_types={"Amount": "num"},
        filter_types=ABFilterableDataFrameView.FILTER_TYPES,
        selected_column=3,
    )
    qtbot.addWidget(manager)

    assert manager.tab_widget.currentIndex() == 1
    assert [manager.tab_widget.tabText(i) for i in range(2)] == ["名称", "数值"]

    amount_filter = manager.tabs[1].filter_rows[0]
    amount_filter.filter_query_line.setText("2")
    state = manager.get_filters
    assert state[3]["filters"] == [(FilterOperator.NUM_EQUALS, "2")]
    assert state["mode"] == FilterMode.AND


def test_cf_amount_edit_uses_raw_column_identity(monkeypatch):
    calls = []

    class Cell:
        def column(self):
            return 3

    class Model:
        HEADERS = ["Name", "Category", "Database", "Amount"]

        def headerData(self, *_args):
            raise AssertionError("Display text must not be used as a column key")

        def get_value(self, _cell):
            return 2.5

    holder = SimpleNamespace(
        model=Model(),
        selectedIndexes=lambda: [Cell()],
        method_name=lambda: ("method",),
        selected_cfs=lambda: [("db", "flow")],
    )
    monkeypatch.setattr(
        "activity_browser.ui.tables.impact_categories.actions.CFAmountModify.run",
        staticmethod(
            lambda method, cfs, amount: calls.append((method, cfs, amount))
        ),
    )

    MethodCharacterizationFactorsTable.cell_edited(holder)
    assert calls == [(("method",), [("db", "flow")], 2.5)]


def test_contribution_pseudo_unit_requires_explicit_display_marker(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.base._",
        lambda value: "相对占比" if value == "relative share" else value,
    )
    source = pd.DataFrame(
        {
            "index": ["Score", "Rest (+)", "Rest (-)", "dataset"],
            "unit": ["", "", "", "relative share"],
            "result": [4.0, 1.0, -1.0, 2.0],
        }
    )

    scientific_unit = ContributionModel()
    scientific_unit.sync(
        source.copy(), unit="relative share", translate_unit=False
    )
    unit_column = scientific_unit._dataframe.columns.get_loc("unit")
    assert (
        scientific_unit.data(scientific_unit.index(3, unit_column), Qt.DisplayRole)
        == "relative share"
    )

    display_unit = ContributionModel()
    display_unit.sync(source.copy(), unit="relative share", translate_unit=True)
    assert (
        display_unit.data(display_unit.index(3, unit_column), Qt.DisplayRole)
        == "相对占比"
    )


def test_plot_copies_translate_only_builtin_result_rows(monkeypatch):
    translations = {
        "Score": "得分",
        "Rest (+)": "其余（正）",
        "Rest (-)": "其余（负）",
    }
    monkeypatch.setattr(
        "activity_browser.ui.figures._",
        lambda value: translations.get(value, value),
    )
    source = pd.DataFrame(
        {
            "index": ["Score", "Rest (+)", "Rest (-)", "Score", "Rest (+)"],
            "unit": ["", "", "", "kg", "kg"],
            "result": [5.0, 1.0, -1.0, 2.0, 3.0],
        }
    )
    original = source.copy(deep=True)

    contribution, grey_rows = prepare_contribution_plot_dataframe(source)
    assert list(contribution.index) == [
        "其余（正）",
        "其余（负）",
        "Score",
        "Rest (+)",
    ]
    assert grey_rows == (0, 1)

    heatmap_source = source.assign(
        amount=[1.0] * len(source),
        name=["dataset"] * len(source),
        database=["database"] * len(source),
    )
    heatmap = prepare_lca_results_plot_dataframe(heatmap_source)
    assert list(heatmap.index) == [
        "其余（正）",
        "其余（负）",
        "Score",
        "Rest (+)",
    ]
    assert "amount" not in heatmap.columns
    pd.testing.assert_frame_equal(source, original)

    # Without the recognized prefix these are scientific labels, and a numeric
    # result column named ``amount`` is not mistaken for overview metadata.
    user_only = pd.DataFrame(
        {"index": ["Score", "Rest (+)"], "amount": [2.0, 3.0]}
    )
    user_heatmap = prepare_lca_results_plot_dataframe(user_only)
    assert list(user_heatmap.index) == ["Score", "Rest (+)"]
    assert list(user_heatmap.columns) == ["amount"]


def test_tree_display_translation_keeps_raw_user_role(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.base._",
        lambda value: "未分类" if value == "No classification" else value,
    )
    model = BaseTreeModel()
    model.HEADERS = ["name"]
    model.TRANSLATABLE_VALUES = ("No classification",)
    model.root = TreeItem.build_root(model.HEADERS)
    child = TreeItem(["No classification"], model.root)
    model.root.appendChild(child)
    index = model.index(0, 0, QModelIndex())

    assert model.data(index, Qt.DisplayRole) == "未分类"
    assert model.data(index, Qt.UserRole) == "No classification"


def test_scenario_filename_placeholder_is_visible_plain_text(qtbot, monkeypatch):
    from activity_browser.layouts.tabs import LCA_setup

    monkeypatch.setattr(
        LCA_setup,
        "_",
        lambda value: "〈文件名〉" if value == "〈filename〉" else value,
    )
    widget = LCA_setup.ScenarioImportWidget(0)
    qtbot.addWidget(widget)

    assert widget.scenario_name.text() == "〈文件名〉"


def test_methods_list_keeps_internal_tuple_column_hidden(qtbot):
    table = MethodsTable()
    qtbot.addWidget(table)

    assert table.isColumnHidden(table.model.method_col)
    assert "method" not in table.model.filterable_columns

    table.sync()
    assert table.isColumnHidden(table.model.method_col)


def test_missing_calculation_setup_objects_localize_display_only(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.ui.tables.models.lca_setup._",
        lambda source, **values: (
            "未找到：{value}".format(**values)
            if source == "NOT FOUND: {value}"
            else source.format(**values)
        ),
    )

    activity_key = ("missing-db", "missing-code")
    activity = CSActivityModel()
    activity._dataframe = pd.DataFrame(
        [
            {
                "Amount": 1.0,
                "Unit": "",
                "Product": "",
                "Activity": f"NOT FOUND: {activity_key}",
                "Location": "",
                "Database": "missing-db",
                "key": activity_key,
            }
        ],
        columns=activity.HEADERS,
    )
    activity.key_col = activity._dataframe.columns.get_loc("key")
    activity_column = activity._dataframe.columns.get_loc("Activity")
    activity_index = activity.index(0, activity_column)

    assert activity.data(activity_index, Qt.DisplayRole).startswith("未找到：")
    assert activity.data(activity_index, "sorting").startswith("NOT FOUND:")
    assert activity._dataframe.iat[0, activity_column].startswith("NOT FOUND:")

    method_key = ("missing method",)
    method = CSMethodsModel()
    method._dataframe = pd.DataFrame(
        [
            {
                "Name": f"NOT FOUND: {method_key}",
                "Unit": "Unknown",
                "# CFs": 0,
                "method": method_key,
            }
        ],
        columns=method.HEADERS,
    )
    method_index = method.index(0, method._dataframe.columns.get_loc("Name"))

    assert method.data(method_index, Qt.DisplayRole).startswith("未找到：")
    assert method.data(method_index, "sorting").startswith("NOT FOUND:")

    # A valid user object whose name starts with the same words is data, not UI.
    method._methods[method_key] = object()
    assert method.data(method_index, Qt.DisplayRole).startswith("NOT FOUND:")


def test_parameter_scenario_row_mismatch_uses_fixed_translatable_message(
    monkeypatch
):
    from activity_browser.layouts.tabs import parameters as parameter_tabs
    from activity_browser.ui.tables.models.scenarios import TooManyParametersError

    def reject_scenario(**_kwargs):
        raise TooManyParametersError

    messages = []
    holder = SimpleNamespace(
        tbl=SimpleNamespace(model=SimpleNamespace(sync=reject_scenario)),
        build_flow_scenarios=lambda: None,
    )
    translations = {
        "Cannot load parameters": "无法加载参数",
        "The scenario file contains more parameter rows than the current project.": (
            "情景文件中的参数行数多于当前项目，无法加载。"
        ),
    }
    monkeypatch.setattr(
        parameter_tabs, "_", lambda source: translations.get(source, source)
    )
    monkeypatch.setattr(
        parameter_tabs.QMessageBox,
        "critical",
        lambda _parent, title, detail, *_buttons: messages.append((title, detail)),
    )

    parameter_tabs.ParameterScenariosTab.process_scenarios(
        holder, 0, pd.DataFrame(), False
    )

    assert messages == [
        ("无法加载参数", "情景文件中的参数行数多于当前项目，无法加载。")
    ]


def test_chinese_plot_font_fallbacks_are_configured():
    import matplotlib.pyplot as plt

    original = list(plt.rcParams["font.sans-serif"])
    original_unicode_minus = plt.rcParams["axes.unicode_minus"]
    try:
        configure_plot_fonts("zh_CN")
        configured = list(plt.rcParams["font.sans-serif"])
        assert configured[: len(CHINESE_PLOT_FONTS)] == list(CHINESE_PLOT_FONTS)
        assert "DejaVu Sans" in configured
        assert plt.rcParams["axes.unicode_minus"] is False
    finally:
        plt.rcParams["font.sans-serif"] = original
        plt.rcParams["axes.unicode_minus"] = original_unicode_minus


def test_uncertainty_delegate_translates_display_only(monkeypatch):
    from stats_arrays import uncertainty_choices

    raw_description = uncertainty_choices[0].description
    monkeypatch.setattr(
        "activity_browser.ui.tables.delegates.uncertainty._",
        lambda value: "无不确定性" if value == raw_description else value,
    )
    delegate = UncertaintyDelegate()

    assert delegate.displayText(0, None) == "无不确定性"
    assert delegate.choices[raw_description] == 0


def test_uncertainty_delegate_stores_item_id_not_translated_text(qtbot):
    from stats_arrays import uncertainty_choices

    choice = next(item for item in uncertainty_choices if item.id > 0)
    editor = QtWidgets.QComboBox()
    qtbot.addWidget(editor)
    editor.addItem("已翻译的不确定性类型", choice.id)

    model = QStandardItemModel(1, 1)
    index = model.index(0, 0)
    UncertaintyDelegate().setModelData(editor, model, index)

    assert model.data(index, Qt.EditRole) == choice.id
