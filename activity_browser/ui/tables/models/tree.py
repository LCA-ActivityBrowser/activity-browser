# -*- coding: utf-8 -*-
from PySide2.QtCore import Qt

from .base import BaseTreeModel, TreeItem


class ImpactCategoryItem(TreeItem):
    """ Item in MethodsTreeModel."""
    # this manual typing of COLUMNS below could be a risk later:
    # potential fix could be to get data from HEADERS in tables/impact_categories/MethodsTree
    COLUMNS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @classmethod
    def build_item(cls, impact_cat, parent: TreeItem) -> 'ImpactCategoryItem':
        item = cls(list(impact_cat), parent)
        parent.appendChild(item)
        return item


class MethodsTreeModel(BaseTreeModel):
    """
    Tree model for impact categories.
    Tree is auto generated in tables/impact_categories/MethodsTree
    """
    def __init__(self, data: dict, parent=None):
        super().__init__(data, parent)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled

    def setup_model_data(self, data: dict) -> None:
        """ First construct the root, then process the data.
        """
        self.root = ImpactCategoryItem.build_root()

        self.build_tree(data, self.root)

    def build_tree(self, data: dict, root):
        for key in data.keys():

            if type(data[key]) == dict:
                # this manual length setting of the list below could be a risk later:
                # potential fix could be to get length from HEADERS in tables/impact_categories/MethodsTree
                new_root = root.build_item([key, '', '', ''], root)
                self.build_tree(data[key], new_root)
            else:
                leaf = data[key]
                ImpactCategoryItem.build_item(leaf, root)
