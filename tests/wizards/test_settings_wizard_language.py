from activity_browser.ui.wizards import settings_wizard


class FakeSettings:
    current_bw_dir = "/brightway"
    custom_bw_dir = ["/brightway"]
    startup_project = "default"
    language = "system"

    def __init__(self):
        self.write_count = 0

    def write_settings(self):
        self.write_count += 1


class FakeComboBox:
    def currentData(self):
        return "zh_CN"

    def currentText(self):
        # A translated display value must never be written as program state.
        return "简体中文"


class FakePage:
    language_combo = FakeComboBox()


class FakeWizard:
    settings_page = FakePage()

    def field(self, name):
        return {"current_bw_dir": "/brightway", "startup_project": "default"}[name]


def test_settings_wizard_saves_language_item_data(monkeypatch):
    fake_settings = FakeSettings()
    switched_directories = []
    monkeypatch.setattr(settings_wizard, "ab_settings", fake_settings)
    monkeypatch.setattr(
        settings_wizard.projects, "switch_dir", switched_directories.append
    )

    settings_wizard.SettingsWizard.save_settings(FakeWizard())

    assert fake_settings.language == "zh_CN"
    assert fake_settings.language != "简体中文"
    assert fake_settings.write_count == 1
    assert switched_directories == ["/brightway"]
