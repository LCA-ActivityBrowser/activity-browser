# -*- coding: utf-8 -*-
from .models import LCAResultsModel, InventoryModel, ContributionModel
from .views import ABDataFrameView, ABFilterableDataFrameView


class LCAResultsTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = LCAResultsModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)


class InventoryTable(ABFilterableDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = InventoryModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
        self.model.updated.connect(self.update_filter_data)
        # below variables are required for switching between technosphere and biosphere tables
        self.showing = None
        self.filters_tec = None
        self.filters_bio = None

    def update_filter_data(self) -> None:
        if self.showing == 'technosphere':
            self.filters = self.filters_tec
        else:
            self.filters = self.filters_bio

        # update the column header indices
        if isinstance(self.model.filterable_columns, dict):
            self.header.column_indices = list(self.model.filterable_columns.values())
        # apply the existing filters
        self.apply_filters()

    def write_filters(self, filters: dict) -> None:
        if self.showing == 'technosphere':
            self.filters_tec = filters
        else:
            self.filters_bio = filters
        self.filters = filters


class ContributionTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ContributionModel(parent=self)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)
