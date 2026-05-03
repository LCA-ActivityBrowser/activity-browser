from typing import Optional
from loguru import logger

import pandas as pd

from PySide6 import QtGui
from PySide6.QtCore import QModelIndex, Qt, QAbstractItemModel
from PySide6.QtWidgets import QWidget

from activity_browser.ui.icons import qicons


class TreeNode:
    """
    Optimized node object that combines children_map, row_indices, loaded_counts, 
    and DataFrame position for O(1) lookups.
    """
    __slots__ = ('path', 'children', 'row_in_parent', 'loaded_count', 'df_position', 'is_leaf', '_child_lookup')
    
    def __init__(self, path: tuple, df_position: int = -1):
        self.path: tuple = path  # Full path tuple for this node
        self.children: list['TreeNode'] = []  # List of child nodes
        self.row_in_parent: int = -1  # Row index within parent's children list
        self.loaded_count: int = 0  # Number of children currently loaded (for lazy loading)
        self.df_position: int = df_position  # Integer position in DataFrame (-1 for branch nodes)
        self.is_leaf: bool = (df_position >= 0)  # True if this is a leaf node
        self._child_lookup: dict[tuple, TreeNode] = {}  # Fast child lookup by path
    
    def add_child(self, child: 'TreeNode') -> None:
        """Add a child node and update its row_in_parent."""
        child.row_in_parent = len(self.children)
        self.children.append(child)
        self._child_lookup[child.path] = child
    
    def get_child(self, path: tuple) -> Optional['TreeNode']:
        """Get a child by its path (O(1) lookup)."""
        return self._child_lookup.get(path)
    
    def get_child_at(self, row: int) -> Optional['TreeNode']:
        """Get a child by its row index (O(1) lookup)."""
        if 0 <= row < len(self.children):
            return self.children[row]
        return None
    
    def total_children(self) -> int:
        """Total number of children (for lazy loading comparison)."""
        return len(self.children)
    
    def can_fetch_more(self) -> bool:
        """Check if more children can be loaded."""
        return self.loaded_count < len(self.children)


class ABTreeModel(QAbstractItemModel):
    def __init__(self,
                 df: pd.DataFrame = None,
                 parent: Optional[QWidget] = None,
                 chunk_size: int = -1,
                 enable_sorting: bool = False
                 ) -> None:
        super().__init__(parent)
        self.df = df if df is not None else pd.DataFrame()
        self.df.index = pd.MultiIndex.from_arrays([range(len(self.df))], names=[f"index"])

        self.df_query: dict[str, str] = {"model": "index == index"}  # dictionary where queries can be registered
        self.filtered_columns: set[int] = set()  # set of column indices that have active filters, only used for the header icon
        self.grouped_columns: list[str] = []  # list of columns currently used for grouping

        self.sorted_column: str | None = None
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.sorting_enabled = enable_sorting

        self.lazy = chunk_size > 0
        self.chunk_size = chunk_size
        
        # Single unified node map: path -> TreeNode
        self.node_map: dict[tuple, TreeNode] = {}
        self.root: TreeNode = TreeNode(tuple())  # Root node with empty path
        
        # Build the node hierarchy
        self.build_node_hierarchy(self.df.index)
    
    def columns(self) -> list[str]:
        """Return the list of column names, including the tree column."""
        return ["index"] + [col for col in self.df.columns if not col.startswith("_")]

    def column_name(self, index: QModelIndex) -> str:
        """Return the name of the column at the given index, including the tree column."""
        return self.columns()[index.column()]
    
    def row(self, index: QModelIndex) -> pd.Series | None:
        """
        Return the DataFrame row corresponding to the given index, or None for non-leaf nodes.
        
        Warning: This is a slow operation and should be avoided in methods called frequently like data(), *Data(), flags(), or index*().
        """
        if not index.isValid():
            return None
        
        node = index.internalPointer()
        
        if not isinstance(node, TreeNode) or not node.is_leaf:
            return None
        
        # Use the pre-computed df_position for fast access
        return self.df.iloc[node.df_position]
    
    def get(self, index: QModelIndex, column: str | int) -> any:
        """
        Get the data for the given QModelIndex and column name or index.
        """
        if not index.isValid():
            return None
        
        node = index.internalPointer()
        
        if not isinstance(node, TreeNode) or not node.is_leaf:
            return None
        
        column_i = column if isinstance(column, int) else self.df.columns.get_loc(column)

        return self.df.iat[node.df_position, column_i]


    # --- required model overrides ---
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        parent_node = parent.internalPointer() if parent.isValid() else self.root
        
        if not isinstance(parent_node, TreeNode):
            parent_node = self.root
        
        child_node = parent_node.get_child_at(row)
        
        if child_node is None:
            return QModelIndex()

        return self.createIndex(row, column, child_node)

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        node = index.internalPointer()
        if not isinstance(node, TreeNode):
            return QModelIndex()
        
        parent_path = self.parent_path(node.path)

        if len(parent_path) == 0:
            return QModelIndex()

        parent_node = self.node_map.get(parent_path)
        if parent_node is None:
            return QModelIndex()

        return self.createIndex(parent_node.row_in_parent, 0, parent_node)
    
    def parent_path(self, path: tuple) -> tuple:
        path = tuple(val for val in path if not pd.isna(val))
        return path[:-1]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        # For tree models, when the parent is valid and column > 0, return 0
        if parent.isValid() and parent.column() != 0:
            return 0

        parent_node = parent.internalPointer() if parent.isValid() else self.root
        
        if not isinstance(parent_node, TreeNode):
            parent_node = self.root

        # Return the number of currently loaded children
        return parent_node.loaded_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 (Qt signature)      
        # Always return the full column count for consistent tree structure
        return len(self.columns())

    #--- data overrides ---
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        # if not index.isValid() or self.df.empty:
        #     return None
        
        if role == Qt.DisplayRole:
            return self.displayData(index)
        elif role == Qt.EditRole:
            return self.editData(index)
        elif role == Qt.UserRole:
            return self.userData(index)
        elif role == Qt.DecorationRole:
            return self.decorationData(index)
        elif role == Qt.FontRole:
            return self.fontData(index)
        elif role == Qt.ToolTipRole:
            return self.toolTipData(index)

        return None
    
    def displayData(self, index: QModelIndex) -> any:
            node = index.internalPointer()

            if not isinstance(node, TreeNode):
                return None

            if not node.is_leaf: # branch node
                # For branch nodes, show the name in the first column only
                # (spanning will be handled by the view)
                return node.path[-1] if index.column() == 0 else None
            
            if index.column() == 0:
                return None  # leaf node tree column is empty

            # Get the pandas column index (disregard hidden columns)
            col_name = self.columns()[index.column()]
            col_idx = self.df.columns.get_loc(col_name)
            
            val = self.df.iat[node.df_position, col_idx]

            if not hasattr(val, "__iter__") and pd.isna(val):
                return None

            return val

    def editData(self, index: QModelIndex) -> any:
        return self.displayData(index)
    
    def userData(self, index: QModelIndex) -> any:
        return self.displayData(index)
    
    def decorationData(self, index: QModelIndex) -> any:
        return None
    
    def fontData(self, index: QModelIndex) -> any:
        return None
    
    def toolTipData(self, index: QModelIndex) -> any:
        return None
    
    #--- flag overrides ---
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        flags = Qt.ItemFlag.NoItemFlags
        if self.indexEnabled(index):
            flags |= Qt.ItemFlag.ItemIsEnabled
        if self.indexSelectable(index):
            flags |= Qt.ItemFlag.ItemIsSelectable
        if self.indexEditable(index):
            flags |= Qt.ItemFlag.ItemIsEditable
        if self.indexDragEnabled(index):
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        if self.indexDropEnabled(index):
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        if self.indexUserCheckable(index):
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags
    
    def indexEnabled(self, index: QModelIndex) -> bool:
        return True
    
    def indexSelectable(self, index: QModelIndex) -> bool:
        return True
    
    def indexEditable(self, index: QModelIndex) -> bool:
        return False
    
    def indexDragEnabled(self, index: QModelIndex) -> bool:
        return False

    def indexDropEnabled(self, index: QModelIndex) -> bool:
        return False
    
    def indexUserCheckable(self, index: QModelIndex) -> bool:
        return False
    
    def isBranchNode(self, index: QModelIndex) -> bool:
        """Check if the given index represents a branch node (non-leaf)."""
        if not index.isValid():
            return False
        node = index.internalPointer()
        if not isinstance(node, TreeNode):
            return False
        return not node.is_leaf

    def headerData(self, section: int, orientation: Qt.Orientation = Qt.Horizontal, role: int = Qt.DisplayRole):
        if orientation == Qt.Vertical:
            return None

        if role == Qt.DisplayRole:
            if section == 0:
                return ""

            return self.columns()[section]

        if role == Qt.ItemDataRole.FontRole and section in self.filtered_columns:
            font = QtGui.QFont()
            font.setUnderline(True)
            return font

        if role == Qt.ItemDataRole.DecorationRole and section in self.filtered_columns:
            return qicons.filter

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Check if this parent has more children that can be loaded."""
        if not self.lazy:
            return False
        
        parent_node = parent.internalPointer() if parent.isValid() else self.root
        
        if not isinstance(parent_node, TreeNode):
            parent_node = self.root
        
        return parent_node.can_fetch_more()

    def fetchMore(self, parent: QModelIndex) -> None:
        """Load the next chunk of children when user scrolls."""
        if not self.lazy:
            return
        
        parent_node = parent.internalPointer() if parent.isValid() else self.root
        
        if not isinstance(parent_node, TreeNode):
            parent_node = self.root
        
        total_children = parent_node.total_children()
        currently_loaded = parent_node.loaded_count
        
        if currently_loaded >= total_children:
            return  # Everything already loaded
        
        # Calculate how many more to load
        remaining = total_children - currently_loaded
        to_load = min(self.chunk_size, remaining)
        
        # Notify view that we're about to add rows
        first_new_row = currently_loaded
        last_new_row = currently_loaded + to_load - 1
        
        self.beginInsertRows(parent, first_new_row, last_new_row)
        parent_node.loaded_count = currently_loaded + to_load
        self.endInsertRows()

    # --- helper functions ---
    def set_dataframe(self, df: pd.DataFrame, group: list[str] = None) -> None:
        self.beginResetModel()

        self.df = df
        self.grouped_columns = group or self.grouped_columns

        self.build_df_index()
        self.apply_sort()
        self.apply_filter()

        self.endResetModel()

    def update_dataframe(self, df: pd.DataFrame, group: list[str] = None) -> None:
        self.layoutAboutToBeChanged.emit()
        self.df = df
        self.grouped_columns = group or self.grouped_columns

        self.build_df_index()
        self.apply_sort()
        self.apply_filter()

        self.layoutChanged.emit()

    def group(self, columns: list[str] = None) -> None:
        self.layoutAboutToBeChanged.emit()
        self.grouped_columns = columns or self.grouped_columns

        self.build_df_index()
        self.apply_sort()
        self.apply_filter()

        self.layoutChanged.emit()

    def ungroup(self) -> None:
        self.layoutAboutToBeChanged.emit()
        self.grouped_columns = []

        self.build_df_index()
        self.apply_sort()
        self.apply_filter()

        self.layoutChanged.emit()

    def sort(self, column: int | str, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self.sorting_enabled:
            logger.warning(f"Called sort() on {self.__class__.__name__} with sorting disabled.")
            return

        self.layoutAboutToBeChanged.emit()

        self.sorted_column = self.headerData(column) if isinstance(column, int) else column
        self.sort_order = order

        self.apply_sort()
        self.apply_filter()

        self.layoutChanged.emit()

    def filter(self, key: str = None, query: str = None) -> None:
        """Filter the DataFrame based on a simple substring match across all columns."""
        self.layoutAboutToBeChanged.emit()

        if query is not None and key is not None:
            self.df_query[key] = query

        self.apply_filter()

        self.layoutChanged.emit()

    def build_df_index(self):
        # dataframe we will use to build the new index
        df = self.df[self.grouped_columns].copy()

        # unpack iterables in the grouped columns
        for col in self.grouped_columns:
            # Check if the column contains iterables (excluding strings)
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if not isinstance(sample_val, (list, tuple, set)):
                continue

            # Unpack the iterable into separate columns and add to the dataframe
            unpacked = pd.DataFrame(df[col].tolist(), index=df.index)
            for i, unpacked_col in enumerate(unpacked.columns):
                df[f"{col}_{i}"] = unpacked[unpacked_col]

            # Remove the original column from the dataframe
            df = df.drop(columns=[col])

        df = df.dropna(how='all', axis=1)
        df["index"] = range(len(df))

        new_index = pd.MultiIndex.from_frame(df)
        new_index.names = [i + "_i" for i in new_index.names]

        self.df.index = new_index

    def reset_hierarchy(self, df: pd.DataFrame = None) -> None:
        df = df if df is not None else self.df
        old_persistent_indices = [(idx, idx.internalPointer()) for idx in self.persistentIndexList()]

        # Rebuild the node hierarchy
        self.build_node_hierarchy(df.index)

        # Update persistent indexes
        new_persistent = []
        for old_index, old_node in old_persistent_indices:
            if isinstance(old_node, TreeNode):
                # Try to find the same path in the new hierarchy
                new_node = self.node_map.get(old_node.path)
                if new_node is not None:
                    new_index = self.createIndex(new_node.row_in_parent, old_index.column(), new_node)
                    new_persistent.append(new_index)
                else:
                    new_persistent.append(QModelIndex())
            else:
                new_persistent.append(QModelIndex())

        # Update the model's persistent indexes
        self.changePersistentIndexList(self.persistentIndexList(), new_persistent)

    def build_node_hierarchy(self, pandas_index: pd.Index) -> None:
        """
        Build the unified TreeNode hierarchy with all information combined:
        - children relationships
        - row indices
        - loaded counts
        - DataFrame positions
        """
        self.root = TreeNode(tuple())
        self.node_map = {tuple(): self.root}

        # Convert index to frame once for all operations
        idx_df = pandas_index.to_frame(index=False)

        # Create a mapping from full path to DataFrame position
        path_to_position = {}
        for row_tuple in idx_df.itertuples(index=False, name=None):
            df_pos = self.df.index.get_loc(row_tuple)
            path_to_position[row_tuple] = df_pos

        # Process each level to build the hierarchy
        for level in range(idx_df.shape[1]):
            # Get unique child paths at this level (as tuples)
            child_paths = idx_df.iloc[:, :level + 1].drop_duplicates()
            child_tuples = list(child_paths.itertuples(index=False, name=None))

            for child_path in child_tuples:
                if pd.isna(child_path[-1]):
                    continue  # skip NaN children

                # Skip if we've already created this node
                if child_path in self.node_map:
                    continue

                # Determine parent path
                if level == 0:
                    parent_path = tuple()
                else:
                    parent_path = tuple(val for val in child_path[:-1] if not pd.isna(val))

                # Get or create parent node
                parent_node = self.node_map.get(parent_path)
                if parent_node is None:
                    parent_node = self.root

                # Check if this is a leaf node (full depth)
                is_leaf = (level == idx_df.shape[1] - 1)
                df_position = path_to_position.get(child_path, -1) if is_leaf else -1

                # Create the child node
                child_node = TreeNode(child_path, df_position)

                # Add child to parent
                parent_node.add_child(child_node)

                # Store in node map
                self.node_map[child_path] = child_node

        # Initialize loaded counts
        if self.lazy:
            # Load first chunk for each node
            for node in self.node_map.values():
                node.loaded_count = min(self.chunk_size, node.total_children())
        else:
            # All children loaded
            for node in self.node_map.values():
                node.loaded_count = node.total_children()

    def apply_filter(self):
        pandas_query = " & ".join(self.df_query.values())
        filtered_df = self.df.query(pandas_query)
        self.reset_hierarchy(filtered_df)

    def apply_sort(self):
        if self.df.empty or not self.sorting_enabled:
            return

        logger.debug(f"Applying sorting in : {self.__class__.__name__}")

        # Extract the unique order of higher levels
        higher_levels = self.df.index.droplevel(-1).unique() if self.df.index.nlevels > 1 else [None]

        # Build a new index by sorting only within each higher level
        sorted_index = []

        for lvl in higher_levels:
            mask = self.df.index.droplevel(-1) == lvl if lvl is not None else self.df.index
            partial_df = self.df.loc[mask, self.sorted_column or self.df.columns[0]].copy()
            if self.sorted_column is not None:

                partial_df.sort_values(
                # for some reason self.sort_order is always "descending", so I changed == to !=
                    ascending=(self.sort_order != Qt.SortOrder.AscendingOrder),
                    inplace=True,
                    # key=lambda col: col.str.lower()   # could use this to avoid sorting A-Z and then a-z, but it does not work with tuples (keys)
                )
            else:
                partial_df = partial_df.sort_index(ascending=(self.sort_order == Qt.SortOrder.AscendingOrder))
            sorted_index.append(partial_df.index)

        sorted_index = sorted_index[0].append(sorted_index[1:])  # Flatten
        self.df = self.df.loc[sorted_index]  # Update dataframe to new sorted order

    def values_from_indices(self, key: str, indices: list[QModelIndex]):
        """
        Returns the values from the given indices.

        Args:
            key (str): The key to get the values for.
            indices (list[QtCore.QModelIndex]): The indices to get the values for.

        Returns:
            list: The list of values.
        """
        df_positions = []
        for index in indices:
            if not index.isValid():
                continue
            node = index.internalPointer()
            if isinstance(node, TreeNode) and node.is_leaf:
                df_positions.append(node.df_position)
        
        if not df_positions:
            return []
        
        return self.df.iloc[df_positions][key].tolist()

