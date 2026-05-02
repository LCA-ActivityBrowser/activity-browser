import copy
import json
import bw2data as bd
import bw2data.signals as bw_signals
import blinker

from activity_browser.bwutils.filesystem import get_project_ab_path, get_appdata_path

defaults = {
    "startup": {
        "brightway_directory": str(bd.projects._base_data_dir),
        "saved_brightway_directories": [str(bd.projects._base_data_dir)],
        "startup_project": "default",
        "shown_panes": ["Databases", "Impact Categories", "Calculation Setups"],
        "shown_pages": ["Welcome", "Parameters", "Settings"],
    },
    "appearance": {
        "theme": "default",
        "pane_tab_position": "bottom",
        "database_products_as_cards": False,
    },
    "metadatastore": {
        "caching_enabled": True,
        "searcher_enabled": True,
    },
    "plugins": {
        "enabled_plugins": [],
    }
}


class Settings:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.global_config = {}
        self.virtual_config = {}
        self.project_config = {}

        self.load_global_settings()
        self.load_virtual_settings()
        self.load_project_settings()

        self.changed = blinker.Signal()

        bw_signals.project_changed.connect(self.load_project_settings)
    
    def __getitem__(self, key):
        if key in self.virtual_config:
            return self.virtual_config[key]
        if key in self.project_config:
            return self.project_config[key]
        if key in self.global_config:
            return self.global_config[key]
        if key in defaults:
            return defaults[key]
        raise KeyError(f"Setting '{key}' not found in any configuration level.")

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            key, subkey = key
        else:
            subkey = "global"

        if subkey == "global":
            self.global_config[key] = value
        elif subkey == "project":
            self.project_config[key] = value
        else:
            raise KeyError("Subkey must be 'global' or 'project'")
    
    def save(self):
        global_path = get_appdata_path() / "settings.json"
        json.dump(self.global_config, open(global_path, "w"), indent=4)

        project_path = get_project_ab_path() / "settings.json"
        json.dump(self.project_config, open(project_path, "w"), indent=4)

        self.changed.send()
    
    def load_global_settings(self):
        global_path = get_appdata_path() / "settings.json"
        self.global_config = json.load(open(global_path)) if global_path.exists() else copy.deepcopy(defaults)

    def load_project_settings(self, *args, **kwargs):
        project_path = get_project_ab_path() / "settings.json"
        self.project_config = json.load(open(project_path)) if project_path.exists() else {}
    
    def load_virtual_settings(self):
        pass  # Implementation later based on environment variables

    def restore_defaults(self):
        self.global_config = copy.deepcopy(defaults)
        global_path = get_appdata_path() / "settings.json"
        json.dump(self.global_config, open(global_path, "w"), indent=4)

        self.project_config = {}
        project_path = get_project_ab_path() / "settings.json"
        project_path.unlink(missing_ok=True)


