from pathlib import Path
import os
import requests
from requests.exceptions import ConnectionError
import pandas as pd
import io
from PySide2 import QtWidgets

from bw2data.filesystem import safe_filename

from .settings import ab_settings
from .info import __version__


def get_base_path() -> Path:
    return Path(__file__).resolve().parents[0]


def read_file_text(file_dir: str) -> str:
    if not file_dir:
        raise ValueError('File path passed is empty')
    file = open(file_dir, mode="r", encoding='UTF-8')
    if not file:
        raise ValueError('File does not exist in the passed path:', file_dir)
    text = file.read()
    file.close()
    return text


def savefilepath(default_file_name: str = "AB_file", file_filter: str = "All Files (*.*)"):
    """A central function to get a safe file path."""
    safe_name = safe_filename(default_file_name, add_hash=False)
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent=None,
        caption='Choose location for saving',
        dir=os.path.join(ab_settings.data_dir, safe_name),
        filter=file_filter,
    )
    return filepath

class UpdateManager():
    def __init__(self):
        self.conda_forge_url = "https://anaconda.org/conda-forge/activity-browser/labels"

        cu = self.current_version
        la = self.fetch_latest()

        print('the current version of AB is >{}<, the latest version of AB is >{}<'.format(cu, la))

    def fetch_latest(self) -> str:
        """Fetch the latest version number from conda forge."""
        try:
            page = requests.get(self.conda_forge_url)  # retrieve the page from the URL
            df = pd.read_html(io.StringIO(page.text))[0]  # read the version table from the HTML
            latest = df.iloc[0, 1]
        except ConnectionError as e:  # failing to connect to server
            # TODO log error properly and handle it properly
            latest = '0.0.0'
        except:  # failing to read the version from the page
            # TODO log error properly and handle it properly
            latest = '0.0.0'
        return latest

    @property
    def current_version(self) -> str:
        """Version of AB running now"""
        return __version__
