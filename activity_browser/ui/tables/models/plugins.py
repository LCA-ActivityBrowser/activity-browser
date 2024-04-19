# -*- coding: utf-8 -*-
from importlib import metadata

import pandas as pd
from PySide2.QtCore import QModelIndex

from activity_browser.settings import project_settings, ab_settings
from activity_browser.signals import qprojects, qparameters
from .base import PandasModel


class PluginsModel(PandasModel):
    HEADERS = ["use", "name", "author", "version"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.plugins_list = []
        qprojects.current_changed.connect(self.sync)
        qparameters.parameters_changed.connect(self.sync)

    def get_plugin_name(self, proxy: QModelIndex) -> str:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), 1]

    def sync(self, index: QModelIndex = None, value: bool = None):
        data = []
        if index is None:
            switches = [name in project_settings.get_plugins_list() for name in ab_settings.plugins.keys()]
        else:
            switches = [switch if j != index.row() else value for j, switch in enumerate(self._dataframe['use'])]
        for i, (name, plugin) in enumerate(ab_settings.plugins.items()):
            infos = {
                "use": switches[i],
                "name": name,
                "author": metadata.metadata(name)["Author"],
                "version": metadata.version(name),
            }
            data.append(infos)

        self._dataframe = pd.DataFrame(data, columns=self.HEADERS)
        self.updated.emit()

    def selected(self):
        return self._dataframe.loc[:, ['use', 'name']]