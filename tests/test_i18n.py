import json
from pathlib import Path

import pytest
from PySide2.QtCore import QCoreApplication, QTranslator

import activity_browser.i18n as i18n


class FakeApplication:
    def __init__(self):
        self.translators = []
        self.removed_translators = []

    def installTranslator(self, translator):
        self.translators.append(translator)
        return True

    def removeTranslator(self, translator):
        self.removed_translators.append(translator)
        if translator in self.translators:
            self.translators.remove(translator)
        return True


class FakeQtTranslator:
    def __init__(self, loadable=()):
        self.loadable = set(loadable)
        self.load_calls = []

    def load(self, catalog_name, translations_path):
        self.load_calls.append((catalog_name, translations_path))
        return catalog_name in self.loadable


def write_catalog(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "system"),
        ("System default", "system"),
        ("system", "system"),
        ("en-US", "en_US"),
        ("en-GB", "en_US"),
        ("en_US.UTF-8", "en_US"),
        ("en", "en_US"),
        ("English", "en_US"),
        ("zh-Hans", "zh_CN"),
        ("zh-Hans-CN", "zh_CN"),
        ("zh-TW", "zh_CN"),
        ("zh_CN.UTF-8", "zh_CN"),
        ("zh_CN", "zh_CN"),
        ("中文", "zh_CN"),
        ("Simplified Chinese", "zh_CN"),
        ("简体中文", "zh_CN"),
        ("unsupported", "system"),
    ],
)
def test_normalize_language(value, expected):
    assert i18n.normalize_language(value) == expected


def test_resolve_system_language():
    assert i18n.resolve_language("system", "zh_CN") == "zh_CN"
    assert i18n.resolve_language("system", "zh-TW") == "zh_CN"
    assert i18n.resolve_language("system", "fr_FR") == "en_US"
    assert i18n.resolve_language("en_US", "zh_CN") == "en_US"


def test_catalog_fragments_qtranslator_and_formatting(tmp_path, monkeypatch):
    write_catalog(tmp_path / "zh_CN.json", {"Save": "保存"})
    write_catalog(
        tmp_path / "zh_CN" / "core.json",
        {"Hello {name}": "你好，{name}", "Missing only in English": "已有翻译"},
    )

    manager = i18n.TranslationManager(tmp_path, system_locale="en_US")
    application = FakeApplication()
    assert manager.install(application, "zh_CN") == "zh_CN"
    assert manager.requested_language == "zh_CN"
    assert manager.current_language == "zh_CN"
    assert manager.gettext("Save") == "保存"
    assert manager.gettext("Hello {name}", name="王明") == "你好，王明"
    assert manager.gettext("No catalog entry") == "No catalog entry"

    catalog_translator = application.translators[-1]
    assert isinstance(catalog_translator, QTranslator)
    assert catalog_translator.translate("context", "Save") == "保存"
    assert catalog_translator.translate("context", "Unknown") is None

    monkeypatch.setattr(i18n, "translation_manager", manager)
    assert i18n._("Hello {name}", name="李华") == "你好，李华"
    assert i18n.current_language() == "zh_CN"


def test_missing_catalog_entry_falls_back_to_qt_source_text():
    application = QCoreApplication.instance()
    earlier_translator = i18n.CatalogTranslator({"Unknown": "较早的翻译"})
    translator = i18n.CatalogTranslator({"Save": "保存"})
    application.installTranslator(earlier_translator)
    application.installTranslator(translator)
    try:
        assert QCoreApplication.translate("context", "Save") == "保存"
        assert QCoreApplication.translate("context", "Unknown") == "较早的翻译"
        assert QCoreApplication.translate("context", "No translation") == (
            "No translation"
        )
    finally:
        application.removeTranslator(translator)
        application.removeTranslator(earlier_translator)


def test_conflicting_catalog_fragments_are_rejected(tmp_path):
    write_catalog(tmp_path / "zh_CN" / "a.json", {"Save": "保存"})
    write_catalog(tmp_path / "zh_CN" / "b.json", {"Save": "存储"})
    manager = i18n.TranslationManager(tmp_path, system_locale="en_US")

    with pytest.raises(i18n.TranslationCatalogError, match="Conflicting translation"):
        manager.load_catalog("zh_CN")


def test_invalid_catalog_shape_is_rejected(tmp_path):
    write_catalog(tmp_path / "zh_CN" / "bad.json", {"Save": 42})
    manager = i18n.TranslationManager(tmp_path, system_locale="en_US")

    with pytest.raises(i18n.TranslationCatalogError, match="map strings to strings"):
        manager.load_catalog("zh_CN")


def test_install_replaces_translators_and_detaches_them_from_the_old_app(
    tmp_path, monkeypatch
):
    write_catalog(tmp_path / "zh_CN" / "core.json", {"Save": "保存"})
    qt_translator = FakeQtTranslator({"qtbase_zh_CN"})
    monkeypatch.setattr(i18n, "QTranslator", lambda: qt_translator)

    manager = i18n.TranslationManager(tmp_path, system_locale="en_US")
    first_application = FakeApplication()
    second_application = FakeApplication()

    assert manager.install(first_application, "zh_CN") == "zh_CN"
    assert [name for name, _path in qt_translator.load_calls] == [
        "qt_zh_CN",
        "qtbase_zh_CN",
    ]
    assert first_application.translators[0] is qt_translator
    chinese_catalog_translator = first_application.translators[1]

    assert manager.install(second_application, "en_US") == "en_US"
    assert first_application.translators == []
    assert first_application.removed_translators == [
        chinese_catalog_translator,
        qt_translator,
    ]
    assert len(second_application.translators) == 1
    assert manager.requested_language == "en_US"
    assert manager.current_language == "en_US"


def test_json_catalog_translates_standard_buttons_when_qt_qm_is_unavailable(
    monkeypatch,
):
    catalog_root = Path(i18n.__file__).resolve().parent / "translations"
    qt_translator = FakeQtTranslator()
    monkeypatch.setattr(i18n, "QTranslator", lambda: qt_translator)

    manager = i18n.TranslationManager(catalog_root, system_locale="en_US")
    application = FakeApplication()
    manager.install(application, "zh_CN")

    # No Qt translator was installed, so the context-independent JSON
    # translator is the fallback for standard QMessageBox/QWizard text.
    assert application.translators == [manager._catalog_translator]
    translator = application.translators[0]
    assert translator.translate("QPlatformTheme", "OK") == "确定"
    assert translator.translate("QPlatformTheme", "Cancel") == "取消"
    assert translator.translate("QDialogButtonBox", "&Cancel") == "取消(&C)"
    assert translator.translate("QWizard", "&Finish") == "完成(&F)"
