# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import Qt

from .base import BaseTreeModel, TreeItem


class ParameterItem(TreeItem):
    COLUMNS = ["Name", "Group", "Amount", "Formula"]

    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @staticmethod
    def build_header(header: str, parent: TreeItem) -> 'ParameterItem':
        item = ParameterItem([header, "", "", ""], parent)
        parent.appendChild(item)
        return item

    @classmethod
    def build_item(cls, param, parent: TreeItem) -> 'ParameterItem':
        """ Depending on the parameter type, the group is changed, defaults to
        'project'.

        For Activity parameters, use a 'header' item as parent, create one
        if it does not exist.
        """
        group = "project"
        if hasattr(param, "code") and hasattr(param, "database"):
            database = "database - {}".format(str(param.database))
            if database not in [x.data(0) for x in parent.children]:
                cls.build_header(database, parent)
            parent = next(x for x in parent.children if x.data(0) == database)
            group = getattr(param, "group")
        elif hasattr(param, "database"):
            group = param.database

        item = cls([
            getattr(param, "name", ""),
            group,
            getattr(param, "amount", 1.0),  # set to 1 instead of 0 as division by 0 causes problems
            getattr(param, "formula", ""),
        ], parent)

        # If the variable is found, we're working on an activity parameter
        if "database" in locals():
            cls.build_exchanges(param, item)

        parent.appendChild(item)
        return item

    @classmethod
    def build_exchanges(cls, act_param, parent: TreeItem) -> None:
        """ Take the given activity parameter, retrieve the matching activity
        and construct tree-items for each exchange with a `formula` field.
        """
        act = bw.get_activity((act_param.database, act_param.code))

        for exc in [exc for exc in act.exchanges() if "formula" in exc]:
            act_input = bw.get_activity(exc.input)
            item = cls([
                act_input.get("name"),
                parent.data(1),
                exc.amount,
                exc.get("formula"),
            ], parent)
            parent.appendChild(item)


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


class ParameterTreeModel(BaseTreeModel):
    """
    Ordering and foldouts as follows:
    - Project parameters:
        - All 'root' objects
        - No children
    - Database parameters:
        - All 'root' objects
        - No children
    - Activity parameters:
        - Never root objects.
        - Placed under simple 'database' root objects
        - Exchanges as children
    - Exchange parameters:
        - Never root objects
        - Children of relevant activity parameter
        - No children
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(data, parent)

    def setup_model_data(self, data: dict) -> None:
        """ First construct the root, then process the data.
        """
        self.root = ParameterItem.build_root()

        for param in data.get("project", []):
            ParameterItem.build_item(param, self.root)
        for param in data.get("database", []):
            ParameterItem.build_item(param, self.root)
        for param in data.get("activity", []):
            try:
                _ = bw.get_activity((param.database, param.code))
            except:
                continue
            ParameterItem.build_item(param, self.root)


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
