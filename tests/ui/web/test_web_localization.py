"""Localization checks for embedded Activity Browser web views."""

import json
from pathlib import Path
from types import SimpleNamespace

from activity_browser.ui.web import base, navigator, sankey_navigator, webutils


STATIC_DIR = Path(__file__).resolve().parents[3] / "activity_browser" / "static"


def test_localized_html_path_prefers_requested_language(tmp_path):
    default = tmp_path / "welcome.html"
    chinese = tmp_path / "welcome.zh_CN.html"
    default.write_text("English", encoding="utf-8")
    chinese.write_text("中文", encoding="utf-8")

    assert webutils.localized_html_path(str(default), "zh_CN") == str(chinese)
    assert webutils.localized_html_path(str(default), "en_US") == str(default)


def test_welcome_pages_are_utf8_and_chinese_page_is_complete():
    english = (STATIC_DIR / "startscreen" / "welcome.html").read_text(encoding="utf-8")
    chinese = (STATIC_DIR / "startscreen" / "welcome.zh_CN.html").read_text(
        encoding="utf-8"
    )

    assert 'charset="utf-8"' in english
    assert "ISO-8859-1" not in english
    assert 'lang="zh-CN"' in chinese
    assert "欢迎使用 Activity Browser" in chinese
    assert "生命周期评价" in chinese
    assert "参与贡献" in chinese


def test_graph_html_injects_only_fixed_ui_translations(monkeypatch):
    translations = {
        "Graph Navigator": "图形浏览器",
        "Reset Zoom": "重置缩放",
        "Download SVG": "下载 SVG",
        "Individual impact": "单项影响",
        "Cumulative impact": "累积影响",
    }
    monkeypatch.setattr(base, "_", lambda source: translations.get(source, source))
    monkeypatch.setattr(base, "current_language", lambda: "zh_CN")
    page = SimpleNamespace(
        HTML_FILE=str(STATIC_DIR / "navigator.html"),
        PAGE_TITLE="Graph Navigator",
    )

    rendered = base.BaseNavigatorWidget.render_html(page)

    assert '<html lang="zh-CN">' in rendered
    assert '<h3 id="heading">图形浏览器</h3>' in rendered
    assert ">重置缩放</button>" in rendered
    assert ">下载 SVG</button>" in rendered
    assert "{{" not in rendered
    embedded = rendered.split("window.abTranslations = ", 1)[1].split(";", 1)[0]
    assert json.loads(embedded) == {
        "individual_impact": "单项影响",
        "cumulative_impact": "累积影响",
    }
    # Local JavaScript assets remain referenced, rather than being translated.
    assert 'src="javascript/d3.js"' in rendered


def test_graph_mode_does_not_depend_on_translated_button_text():
    holder = SimpleNamespace(_expansion_mode=True)
    assert navigator.GraphNavigatorWidget.is_expansion_mode.fget(holder)
    holder._expansion_mode = False
    assert not navigator.GraphNavigatorWidget.is_expansion_mode.fget(holder)


def test_sankey_title_translates_labels_but_preserves_scientific_data(monkeypatch):
    source = (
        "Reference flow: {amount:.2g} {unit} {product} | {activity} | "
        "{location} <br>Total impact: {impact:.2g} {impact_unit}"
    )
    chinese = (
        "参考流：{amount:.2g} {unit} {product} | {activity} | {location} "
        "<br>总影响：{impact:.2g} {impact_unit}"
    )
    monkeypatch.setattr(
        sankey_navigator, "_", lambda value: chinese if value == source else value
    )

    activity = SimpleNamespace(
        get=lambda field: {
            "unit": "kilogram",
            "reference product": "market for electricity",
            "name": "electricity production, wind",
            "location": "CN",
        }.get(field)
    )
    title = sankey_navigator.Graph.build_title((activity, 2.0), 3.5, "kg CO2-Eq")

    assert title.startswith("参考流：")
    assert "market for electricity" in title
    assert "electricity production, wind" in title
    assert "kg CO2-Eq" in title
    assert "总影响：" in title


def test_exchange_tooltip_translates_connector_but_preserves_data(monkeypatch):
    source = "<b>{amount:.3g} {unit} of {product}</b>"
    chinese = "<b>{product}：{amount:.3g} {unit}</b>"
    monkeypatch.setattr(
        navigator, "_", lambda value: chinese if value == source else value
    )

    input_activity = SimpleNamespace(
        key=("ecoinvent", "input"),
        get=lambda field: {
            "reference product": "electricity, high voltage",
            "name": "electricity production",
        }.get(field),
    )
    output_activity = SimpleNamespace(key=("ecoinvent", "output"))

    class Exchange:
        input = input_activity
        output = output_activity

        @staticmethod
        def get(field, default=None):
            return {"amount": 1.25, "unit": "kilowatt hour"}.get(field, default)

    edge = navigator.Graph.build_json_edge(Exchange(), flip_negative=False)

    assert edge["product"] == "electricity, high voltage"
    assert edge["unit"] == "kilowatt hour"
    assert edge["tooltip"] == ("<b>electricity, high voltage：1.25 kilowatt hour</b>")
