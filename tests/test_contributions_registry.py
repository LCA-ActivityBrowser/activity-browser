"""Tests for contribution registries (ticket 10 prefactor seam)."""
import pytest

from activity_browser.app import contributions as contrib


@pytest.fixture(autouse=True)
def _isolate_registries():
    """Keep registry mutations out of other tests' global state."""
    actions = contrib.action_contributions.copy()
    chapters = contrib.settings_chapters.copy()
    menu = list(contrib.plugins_menu_contributions)
    contrib.action_contributions.clear()
    contrib.settings_chapters.clear()
    contrib.plugins_menu_contributions.clear()
    yield
    contrib.action_contributions.clear()
    contrib.action_contributions.update(actions)
    contrib.settings_chapters.clear()
    contrib.settings_chapters.update(chapters)
    contrib.plugins_menu_contributions[:] = menu


def test_register_settings_chapter_is_ordered_and_rejects_duplicates():
    class ChapA:
        pass

    class ChapB:
        pass

    contrib.register_settings_chapter("Startup", ChapA)
    contrib.register_settings_chapter("Plugins", ChapB)
    assert list(contrib.settings_chapters.keys()) == ["Startup", "Plugins"]
    assert contrib.settings_chapters["Plugins"] is ChapB
    with pytest.raises(ValueError, match="already registered"):
        contrib.register_settings_chapter("Startup", ChapA)


def test_register_action_rejects_duplicate_ids():
    class Act:
        pass

    contrib.register_action("ab.manage_plugins", Act)
    with pytest.raises(ValueError, match="already registered"):
        contrib.register_action("ab.manage_plugins", Act)


def test_register_plugins_menu_item_appends():
    contrib.register_plugins_menu_item("Manage plugins…", "ab.manage_plugins")
    assert contrib.plugins_menu_contributions == [
        ("Manage plugins…", "ab.manage_plugins")
    ]


def test_register_base_settings_chapters_is_idempotent():
    from activity_browser.app.pages.settings.base_chapters import (
        BASE_SETTINGS_CHAPTERS,
        register_base_settings_chapters,
    )

    class PluginChapter:
        pass

    contrib.register_settings_chapter("Plugin Example", PluginChapter)
    register_base_settings_chapters()

    for title, chapter_class in BASE_SETTINGS_CHAPTERS:
        assert contrib.settings_chapters[title] is chapter_class
    assert contrib.settings_chapters["Plugin Example"] is PluginChapter

    register_base_settings_chapters()
    assert len(contrib.settings_chapters) == len(BASE_SETTINGS_CHAPTERS) + 1
