# -*- coding: utf-8 -*-
from .models import LCAResultsModel, InventoryModel, ContributionModel
from .views import ABDataFrameView


class LCAResultsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LCAResultsModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)


class InventoryTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = InventoryModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)


class ContributionTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ContributionModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
