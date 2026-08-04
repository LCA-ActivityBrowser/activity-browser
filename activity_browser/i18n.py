# -*- coding: utf-8 -*-
"""Internationalization support for Activity Browser's user interface.

The scientific data handled by Activity Browser deliberately does not pass
through this module.  Catalog keys are the English user-interface strings and
catalog values are their translations.
"""

import json
from importlib import resources
from logging import getLogger
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from PySide2.QtCore import QLibraryInfo, QLocale, QTranslator

log = getLogger(__name__)

SYSTEM_LANGUAGE = "system"
ENGLISH = "en_US"
SIMPLIFIED_CHINESE = "zh_CN"
SUPPORTED_LANGUAGES = (SYSTEM_LANGUAGE, ENGLISH, SIMPLIFIED_CHINESE)

_LANGUAGE_LABELS = {
    SYSTEM_LANGUAGE: "System default",
    ENGLISH: "English",
    SIMPLIFIED_CHINESE: "Simplified Chinese",
}

_LANGUAGE_ALIASES = {
    "": SYSTEM_LANGUAGE,
    "auto": SYSTEM_LANGUAGE,
    "default": SYSTEM_LANGUAGE,
    "system": SYSTEM_LANGUAGE,
    "system_default": SYSTEM_LANGUAGE,
    "跟随系统": SYSTEM_LANGUAGE,
    "系统默认": SYSTEM_LANGUAGE,
    "en": ENGLISH,
    "en_us": ENGLISH,
    "english": ENGLISH,
    "英文": ENGLISH,
    "英语": ENGLISH,
    "zh": SIMPLIFIED_CHINESE,
    "zh_cn": SIMPLIFIED_CHINESE,
    "zh_hans": SIMPLIFIED_CHINESE,
    "chinese": SIMPLIFIED_CHINESE,
    "chinese_(simplified)": SIMPLIFIED_CHINESE,
    "simplified_chinese": SIMPLIFIED_CHINESE,
    "中文": SIMPLIFIED_CHINESE,
    "简体中文": SIMPLIFIED_CHINESE,
}


class TranslationCatalogError(RuntimeError):
    """Raised when translation catalog files cannot be merged safely."""


def normalize_language(language: Optional[str]) -> str:
    """Return a supported stable language code.

    Older display labels and common locale spellings are accepted so existing
    settings can be migrated.  Unknown values safely fall back to ``system``.
    """

    if not isinstance(language, str):
        return SYSTEM_LANGUAGE
    key = language.strip().replace("-", "_").replace(" ", "_").casefold()
    if key in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[key]

    # Accept common regional/script locale forms and POSIX suffixes when
    # migrating settings written by older builds or external launchers.
    locale_key = key.split(".", 1)[0].split("@", 1)[0]
    if locale_key.startswith("en_"):
        return ENGLISH
    if locale_key.startswith("zh_"):
        return SIMPLIFIED_CHINESE
    return SYSTEM_LANGUAGE


def resolve_language(language: Optional[str], system_locale: Optional[str] = None) -> str:
    """Resolve ``system`` to one of the languages for which AB has a catalog."""

    normalized = normalize_language(language)
    if normalized != SYSTEM_LANGUAGE:
        return normalized

    locale_name = system_locale if system_locale is not None else QLocale.system().name()
    locale_name = str(locale_name).replace("-", "_").casefold()
    # A simplified-Chinese catalog is preferable to an English fallback on a
    # Chinese-language system.  Other currently unsupported locales use English.
    return SIMPLIFIED_CHINESE if locale_name.startswith("zh") else ENGLISH


class CatalogTranslator(QTranslator):
    """A Qt translator backed by Activity Browser's JSON catalogs."""

    def __init__(self, catalog: Dict[str, str]):
        super().__init__()
        self._catalog = catalog

    def translate(self, context, source_text, disambiguation=None, n=-1):
        # A null QString (``None`` in PySide) tells Qt to continue to an earlier
        # installed translator or its source-text fallback.  An empty string
        # would instead be treated as a successful blank translation.
        return self._catalog.get(source_text)


class TranslationManager:
    """Load JSON catalogs and install them into a Qt application."""

    def __init__(
        self,
        catalog_root: Optional[Union[str, Path]] = None,
        system_locale: Optional[str] = None,
    ):
        self._catalog_root = Path(catalog_root) if catalog_root is not None else None
        self._system_locale = system_locale
        self._application = None
        self._catalog_translator = None
        self._qt_translator = None
        self._requested_language = SYSTEM_LANGUAGE
        self._current_language = resolve_language(SYSTEM_LANGUAGE, self._system_locale)
        self._catalog = self.load_catalog(self._current_language)

    @property
    def requested_language(self) -> str:
        """The stable setting requested by the user, including ``system``."""

        return self._requested_language

    @property
    def current_language(self) -> str:
        """The language actually in use (``en_US`` or ``zh_CN``)."""

        return self._current_language

    @property
    def catalog(self) -> Dict[str, str]:
        """Return a copy of the active catalog for diagnostics and tests."""

        return dict(self._catalog)

    def _translation_root(self):
        if self._catalog_root is not None:
            return self._catalog_root
        return resources.files("activity_browser.translations")

    def _catalog_files(self, language: str):
        root = self._translation_root()
        files = []

        # A single-file catalog is retained for compatibility.  New catalog
        # contributions should use per-module files in ``<language>/*.json``.
        single_file = root.joinpath(f"{language}.json")
        if single_file.is_file():
            files.append(single_file)

        language_dir = root.joinpath(language)
        if language_dir.is_dir():
            files.extend(
                sorted(
                    (
                        entry
                        for entry in language_dir.iterdir()
                        if entry.is_file() and entry.name.endswith(".json")
                    ),
                    key=lambda entry: entry.name,
                )
            )
        return files

    def load_catalog(self, language: str) -> Dict[str, str]:
        """Load and safely merge all JSON fragments for ``language``."""

        resolved = resolve_language(language, self._system_locale)
        catalog: Dict[str, str] = {}
        origins = {}

        for catalog_file in self._catalog_files(resolved):
            try:
                content = json.loads(catalog_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise TranslationCatalogError(
                    f"Could not read translation catalog {catalog_file}: {exc}"
                ) from exc

            if not isinstance(content, dict):
                raise TranslationCatalogError(
                    f"Translation catalog {catalog_file} must contain a JSON object"
                )

            for source, translation in content.items():
                if not isinstance(source, str) or not isinstance(translation, str):
                    raise TranslationCatalogError(
                        f"Translation catalog {catalog_file} must map strings to strings"
                    )
                if source in catalog and catalog[source] != translation:
                    raise TranslationCatalogError(
                        f"Conflicting translation for {source!r} in "
                        f"{origins[source]} and {catalog_file}"
                    )
                catalog[source] = translation
                origins[source] = catalog_file

        return catalog

    def _remove_installed_translators(self) -> None:
        if self._application is None:
            return
        if self._catalog_translator is not None:
            self._application.removeTranslator(self._catalog_translator)
        if self._qt_translator is not None:
            self._application.removeTranslator(self._qt_translator)
        self._catalog_translator = None
        self._qt_translator = None

    def install(self, application, language: Optional[str] = SYSTEM_LANGUAGE) -> str:
        """Install AB and Qt translations, returning the active language code."""

        requested = normalize_language(language)
        resolved = resolve_language(requested, self._system_locale)
        catalog = self.load_catalog(resolved)

        self._remove_installed_translators()
        self._application = application
        self._requested_language = requested
        self._current_language = resolved
        self._catalog = catalog

        if resolved == SIMPLIFIED_CHINESE:
            qt_translator = QTranslator()
            translations_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
            for catalog_name in ("qt_zh_CN", "qtbase_zh_CN"):
                if qt_translator.load(catalog_name, translations_path):
                    application.installTranslator(qt_translator)
                    self._qt_translator = qt_translator
                    break

        catalog_translator = CatalogTranslator(catalog)
        application.installTranslator(catalog_translator)
        self._catalog_translator = catalog_translator
        log.info(
            "Loaded Activity Browser interface language %s (setting: %s)",
            resolved,
            requested,
        )
        return resolved

    def gettext(self, source: str, **kwargs) -> str:
        """Translate a UI source string and optionally format named fields."""

        if not isinstance(source, str):
            raise TypeError("Translation source must be a string")
        translated = self._catalog.get(source, source)
        return translated.format(**kwargs) if kwargs else translated


translation_manager = TranslationManager()


def _(source: str, **kwargs) -> str:
    """Translate an Activity Browser interface string.

    Named ``str.format`` placeholders are applied after translation, allowing a
    language to reorder values without callers assembling translated fragments.
    """

    return translation_manager.gettext(source, **kwargs)


def current_language() -> str:
    """Return the active concrete language code (``en_US`` or ``zh_CN``)."""

    return translation_manager.current_language


def language_choices() -> Tuple[Tuple[str, str], ...]:
    """Return ``(stable code, translated display name)`` language choices."""

    return tuple((code, _(_LANGUAGE_LABELS[code])) for code in SUPPORTED_LANGUAGES)


__all__ = [
    "_",
    "CatalogTranslator",
    "ENGLISH",
    "SIMPLIFIED_CHINESE",
    "SUPPORTED_LANGUAGES",
    "SYSTEM_LANGUAGE",
    "TranslationCatalogError",
    "TranslationManager",
    "current_language",
    "language_choices",
    "normalize_language",
    "resolve_language",
    "translation_manager",
]
