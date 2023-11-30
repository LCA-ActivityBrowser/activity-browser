from typing import Tuple, Iterable
import requests
from pathlib import Path
import os
from PySide2 import QtWidgets

from bw2data.filesystem import safe_filename

from .settings import ab_settings


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


def safe_link_fetch(url: str) -> Tuple[bool, object]:
    """
    Get a web-page or file from the internet or the error of getting the link.

    Parameters
    ----------
    url: a link

    Returns
    -------
    bool: True if no Exceptions, False if Exceptions
    object: page if no Exceptions, Exception if Exceptions
    """
    try:
        page = requests.get(url)  # retrieve the page from the URL
        return (True, page)
    except Exception as e:
        return (False, e)


def sort_semantic_versions(versions: Iterable) -> list:
    """Return a sorted (descending) list of semantic versions.

    Sorts based on the semantic versioning system.
    """
    return list(sorted(versions, key=lambda x: tuple(map(int, x.split('.'))), reverse=True))
