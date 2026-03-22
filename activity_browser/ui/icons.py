# -*- coding: utf-8 -*-
from pathlib import Path

from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon, QPixmap

PACKAGE_DIR = Path(__file__).resolve().parents[1]


def create_path(folder: str, filename: str) -> str:
    """Builds a path to the image file."""
    return str(PACKAGE_DIR.joinpath("static", "icons", folder, filename))


def empty_icon(size: QSize = QSize(32, 32)) -> QIcon:
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)  # Make the pixmap transparent
    return QIcon(pixmap)


# CURRENTLY UNUSED ICONS

# Modular LCA (keep until this is reintegrated)
# add_db = create_path('metaprocess', 'add_database.png')
# close_db = create_path('metaprocess', 'close_database.png')
# cut = create_path('metaprocess', 'cut.png')
# debug = create_path('main', 'ladybird.png')
# duplicate = create_path('metaprocess', 'duplicate.png')
# graph_lmp = create_path('metaprocess', 'graph_linkedmetaprocess.png')
# graph_mp = create_path('metaprocess', 'graph_metaprocess.png')
# load_db = create_path('metaprocess', 'open_database.png')
# metaprocess = create_path('metaprocess', 'metaprocess.png')
# new = create_path('metaprocess', 'new_metaprocess.png')
# save_db = create_path('metaprocess', 'save_database.png')
# save_mp = create_path('metaprocess', 'save_metaprocess.png')

# key = create_path('main', 'key.png')
# search = create_path('main', 'search.png')
# switch = create_path('main', 'switch-state.png')


class Icons(object):
    # Icons from href="https://www.flaticon.com/

    # MAIN
    ab = create_path("main", "activitybrowser.png")

    # arrows
    right = create_path("main", "right.png")
    left = create_path("main", "left.png")
    forward = create_path("main", "forward.png")
    backward = create_path("main", "backward.png")

    # Simple actions
    delete = create_path("context", "delete.png")
    clear = create_path("context", "clear.png")
    copy = create_path("context", "copy.png")
    add = create_path("context", "add.png")
    edit = create_path("main", "edit.png")
    calculate = create_path("main", "calculate.png")
    question = create_path("context", "question.png")
    search = create_path("main", "search.png")
    filter = create_path("main", "filter.png")
    filter_outline = create_path("main", "filter_outline.png")

    # database
    import_db = create_path("main", "import_database.png")
    duplicate_database = create_path("main", "duplicate_database.png")

    # activity
    duplicate_activity = create_path("main", "duplicate_activity.png")
    duplicate_to_other_database = create_path("main", "import_database.png")
    parameterized = create_path("main", "parameterized.png")

    # windows
    graph_explorer = create_path("main", "graph_explorer.png")
    issue = create_path("main", "idea.png")
    settings = create_path("main", "settings.png")
    history = create_path("main", "history.png")
    welcome = create_path("main", "welcome.png")
    main_window = create_path("main", "home.png")

    # plugins
    plugin = create_path("main", "plugin.png")

    # nodes
    process = create_path("nodes", "process.png")
    product = create_path("nodes", "product.png")
    waste = create_path("nodes", "waste.png")
    processproduct = create_path("nodes", "processproduct.png")
    biosphere = create_path("nodes", "biosphere.png")
    readonly_process = create_path("nodes", "read-only-process.png")

    # other
    superstructure = create_path("main", "superstructure.png")
    copy_to_clipboard = create_path("main", "copy_to_clipboard.png")
    warning = create_path("context", "warning.png")
    critical = create_path("context", "critical.png")
    locked = create_path("main", "locked.png")
    unlocked = create_path("main", "unlocked.png")


class QIcons(Icons):
    """Using the Icons class, returns the same attributes, but as QIcon type"""
    empty = empty_icon()

    def __getattribute__(self, item):
        return QIcon(Icons.__getattribute__(self, item))


icons = Icons()
qicons = QIcons()
