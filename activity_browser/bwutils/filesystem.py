import platformdirs
from pathlib import Path

import bw2data as bd


def get_package_path() -> Path:
    path = Path(__file__).resolve().parents[2]
    path.mkdir(parents=True, exist_ok=True)
    return 

def get_appdata_path() -> Path:
    path = Path(platformdirs.user_data_dir(appname="ActivityBrowser", appauthor="pylca"))
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_project_path() -> Path:
    path =  bd.projects._base_data_dir
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_project_ab_path() -> Path:
    path =  Path(bd.projects._base_data_dir) / "activity_browser"
    path.mkdir(parents=True, exist_ok=True)
    return path
