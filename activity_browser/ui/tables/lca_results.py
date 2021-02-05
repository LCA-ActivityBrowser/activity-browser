# -*- coding: utf-8 -*-
from .models import LCAResultsModel, InventoryModel, ContributionModel
from .views import ABDataFrameView


class LCAResultsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LCAResultsModel(parent=self)
        # self.sync = self.model.sync  # link the model sync method to the table

    def sync(self, df) -> None:
        self.model.sync(df)
        self._resize()


class InventoryTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = InventoryModel(parent=self)

    def sync(self, df) -> None:
        self.model.sync(df)
        self._resize()


class ContributionTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ContributionModel(parent=self)

    def sync(self, df) -> None:
        self.model.sync(df)
        self._resize()








