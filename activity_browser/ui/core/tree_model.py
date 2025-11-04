from typing import Optional
from collections import defaultdict

from loguru import logger
import pandas as pd
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QAbstractItemModel


class ABTreeModel(QAbstractItemModel):
    def __init__(self, df: pd.DataFrame = None, parent: Optional[QWidget] = None, chunk_size: int = -1) -> None:
        super().__init__(parent)
        self.df = df if df is not None else pd.DataFrame()
        self.df_query: dict[str, str] = {"model": "index == index"}  # dictionary where queries can be registered
        self.children_map = self.build_hierarchy_from_index(self.df.index)
        self.lazy = chunk_size > 0
        self.chunk_size = chunk_size
        
        # Track how many children are currently loaded for each parent
        self.loaded_counts: dict[tuple, int] = {}
        if self.lazy:
            # Initially load first chunk for each parent
            for parent_path in self.children_map:
                total = len(self.children_map[parent_path])
                self.loaded_counts[parent_path] = min(chunk_size, total)
        else:
            # All rows are loaded
            for parent_path, children in self.children_map.items():
                self.loaded_counts[parent_path] = len(children)
    
    def columns(self) -> list[str]:
        """Return the list of column names, including the tree column."""
        return ["index"] + list(self.df.columns)

    def column_name(self, index: QModelIndex) -> str:
        """Return the name of the column at the given index, including the tree column."""
        return self.columns()[index.column()]
    
    def row(self, index: QModelIndex) -> pd.Series | None:
        """Return the DataFrame row corresponding to the given index, or None for non-leaf nodes."""
        if not index.isValid():
            return None
        
        path = index.internalPointer()
        
        # Only return data for leaf nodes (full depth paths)
        if len(path) < self.df.index.nlevels:
            return None
        
        return self.df.loc[path]

    # --- required model overrides ---
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_path = parent.internalPointer() or tuple()
        all_children = self.children_map.get(parent_path, [])
                
        if not 0 <= row < len(all_children):
            return QModelIndex()
        
        if parent_path != tuple():
            pass

        # children_map now stores full child paths; use directly
        child_path = all_children[row]

        return self.createIndex(row, column, child_path)


    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        # Full path for the current index
        path = index.internalPointer()
        parent_path = self.parent_path(path)

        if len(parent_path) == 0:
            return QModelIndex()

        grandparent_path = self.parent_path(parent_path)
        grandparent_children = self.children_map.get(grandparent_path, [])
        # children_map stores full paths; find the parent's row among its siblings
        row = grandparent_children.index(parent_path)

        return self.createIndex(row, 0, grandparent_children[row])
    
    def parent_path(self, path: tuple) -> tuple:
        path = tuple(val for val in path if not pd.isna(val))
        return path[:-1]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        # For tree models, when the parent is valid and column > 0, return 0
        if parent.isValid() and parent.column() != 0:
            return 0

        parent_path = parent.internalPointer() or tuple()

        # Return the number of currently loaded children
        return self.loaded_counts.get(parent_path, 0)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 (Qt signature)      
        # Always return the full column count for consistent tree structure
        return len(self.df.columns) + 1  # +1 for tree column

    #--- data overrides ---
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or self.df.empty:
            return None
        
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

        return None
    
    def displayData(self, index: QModelIndex) -> any:
            path = index.internalPointer()
            
            if len(path) < self.df.index.nlevels: # branch node
                return path[-1] if index.column() == 0 else None
            
            if index.column() == 0:
                return None  # leaf node tree column is empty

            col_name = self.headerData(index.column())
            val = self.df.at[path[0] if len(path) == 1 else path, col_name]
            return val

    def editData(self, index: QModelIndex) -> any:
        return self.displayData(index)
    
    def userData(self, index: QModelIndex) -> any:
        return self.displayData(index)
    
    def decorationData(self, index: QModelIndex) -> any:
        return None
    
    def fontData(self, index: QModelIndex) -> any:
        return None
    
    #--- flag overrides ---
    def flags(self, index):
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
    

    def headerData(self, section: int, orientation: Qt.Orientation = Qt.Horizontal, role: int = Qt.DisplayRole):
        if orientation == Qt.Vertical or not role == Qt.DisplayRole:
            return None
        
        if section == 0:
            return "index"
              
        return self.df.columns[section - 1]

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """Check if this parent has more children that can be loaded."""
        if not self.lazy:
            return False
        
        parent_path = parent.internalPointer() or tuple()
        
        # Can fetch more if we have more children than currently loaded
        total_children = len(self.children_map.get(parent_path, []))
        loaded = self.loaded_counts.get(parent_path, 0)
        
        return loaded < total_children

    def fetchMore(self, parent: QModelIndex) -> None:
        """Load the next chunk of children when user scrolls."""
        if not self.lazy:
            return
        
        parent_path = parent.internalPointer() or tuple()
        
        total_children = len(self.children_map.get(parent_path, []))
        currently_loaded = self.loaded_counts.get(parent_path, 0)
        
        if currently_loaded >= total_children:
            return  # Everything already loaded
        
        # Calculate how many more to load
        remaining = total_children - currently_loaded
        to_load = min(self.chunk_size, remaining)
        
        # Notify view that we're about to add rows
        first_new_row = currently_loaded
        last_new_row = currently_loaded + to_load - 1
        
        self.beginInsertRows(parent, first_new_row, last_new_row)
        self.loaded_counts[parent_path] = currently_loaded + to_load
        self.endInsertRows()

    # --- helper functions ---
    def build_hierarchy_from_index(self, pandas_index: pd.Index) -> dict[tuple, list[tuple]]:
        children_map = defaultdict(list)
        
        # Convert index to frame once for all operations
        idx_df = pandas_index.to_frame(index=False)
 
        # Process each level
        for level in range(idx_df.shape[1]):
            # Get unique child paths at this level (as tuples)
            child_paths = idx_df.iloc[:, :level + 1].drop_duplicates()
            child_tuples = list(child_paths.itertuples(index=False, name=None))
            
            if level == 0:
                # Root level - all children belong to empty tuple parent
                children_map[tuple()] = child_tuples
            else:
                # Group children by their parent path
                parent_paths = child_paths.iloc[:, :level]
                parent_tuples = list(parent_paths.itertuples(index=False, name=None))
                
                # Build parent->children mapping efficiently with zip
                for parent, child in zip(parent_tuples, child_tuples):
                    if pd.isna(child[-1]):
                        continue  # skip NaN children
                    parent = tuple(val for val in parent if not pd.isna(val))

                    children_map[parent].append(child)
        
        return dict(children_map)
    
    def reset_hierarchy(self, df: pd.DataFrame = None) -> None:
        df = df if df is not None else self.df

        self.layoutAboutToBeChanged.emit()
        
        old_persistent_paths = [idx.internalPointer() for idx in self.persistentIndexList()]
        
        self.children_map = self.build_hierarchy_from_index(df.index)
        
        # Reset loaded counts for lazy loading
        self.loaded_counts = {}
        if self.lazy:
            # Load first chunk for each parent
            for parent_path in self.children_map:
                total = len(self.children_map[parent_path])
                self.loaded_counts[parent_path] = min(self.chunk_size, total)
        else:
            # All rows loaded
            for parent_path, children in self.children_map.items():
                self.loaded_counts[parent_path] = len(children)

        new_persistent = []
        for path, index in zip(old_persistent_paths, self.persistentIndexList()):
            parent_path = path[:-1]
            if parent_path in self.children_map and path in self.children_map[parent_path]:
                row = self.children_map[parent_path].index(path)
                new_index = self.createIndex(row, index.column(), self.children_map[parent_path][row])
                new_persistent.append(new_index)
            else:
                new_persistent.append(QModelIndex())

        # Update the model's persistent indexes
        self.changePersistentIndexList(self.persistentIndexList(), new_persistent)

        self.layoutChanged.emit()


    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        # Extract the unique order of higher levels
        column_name = self.headerData(column) if column > 0 else self.df.index.names[-1]
        higher_levels = self.df.index.droplevel(-1).unique() if self.df.index.nlevels > 1 else [None]

        # Build a new index by sorting only within each higher level
        sorted_index = []
        
        for lvl in higher_levels:
            mask = self.df.index.droplevel(-1) == lvl if lvl is not None else self.df.index
            partial_df = self.df.loc[mask]
            if column_name is not None:
                partial_df.sort_values(by=column_name, ascending=(order == Qt.SortOrder.AscendingOrder), inplace=True)
            else:
                partial_df = partial_df.sort_index(ascending=(order == Qt.SortOrder.AscendingOrder))
            sorted_index.append(partial_df.index)

        sorted_index = sorted_index[0].append(sorted_index[1:])  # Flatten
        self.df = self.df.loc[sorted_index]  # Update dataframe to new sorted order
        self.filter()

    def filter(self, key: str = None, query: str = None) -> None:
        """Filter the DataFrame based on a simple substring match across all columns."""
        if query is not None and key is not None:
            self.df_query[key] = query
        
        pandas_query = " & ".join(self.df_query.values())
        filtered_df = self.df.query(pandas_query)

        self.reset_hierarchy(filtered_df)

    def quick_filter(self, substring: str) -> None:
        """Quick filter rows containing the substring in any column."""
        if not substring:
            self.filter("index == index")  # reset filter
            return

        query = " or ".join(
            f"`{col}`.astype('string').str.contains({substring!r}, case=False, na=False, regex=False)"
            for col in self.df.columns
        )
        self.filter(query)
    
    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self.df = df
        if not all(self.df.index.names):
            logger.warning("DataFrame index has unnamed levels; resetting to default integer index.")
            self.df.reset_index(drop=True, inplace=True)
            self.df.index.name = "index"

        self.df.index.names = [name + "_i" for name in self.df.index.names]  # append _i to index level names to avoid conflicts

        self.reset_hierarchy()
        self.endResetModel()
    
    def group(self, columns: list[str]) -> None:
        """Regroup the DataFrame by the specified columns.
        
        Unpacks columns containing iterables (lists, tuples, sets) by spreading them
        into separate columns that become separate levels in the multiindex.
        """
        df = self.df[columns].copy()
        
        # Build the list of columns for the new index, unpacking iterables
        for col in columns:              
            # Check if the column contains iterables (excluding strings)
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None

            if not isinstance(sample_val, (list, tuple, set)):
                continue

            # Unpack the iterable into separate columns
            unpacked = pd.DataFrame(df[col].tolist(), index=df.index)
            
            # Name the new columns
            unpacked.columns = [f"{col}_{i}" for i in range(len(unpacked.columns))]
           
            # Add unpacked columns to the dataframe
            for unpacked_col in unpacked.columns:
                df[unpacked_col] = unpacked[unpacked_col]
            
            # Remove the original column from the dataframe
            df = df.drop(columns=[col])
        
        levels = list(df.columns) + list(df.index.names)

        df = df.reset_index()
        df = df[levels]

        new_index = pd.MultiIndex.from_frame(df)
        new_index.names = [i+"_i" if not i.endswith("_i") else i for i in new_index.names]

        self.df = self.df.set_index(new_index)

        self.reset_hierarchy()
    
    def ungroup(self) -> None:
        """Ungroup the DataFrame by resetting the index."""
        self.df.reset_index(drop=True, inplace=True)
        self.df.index.name = "index"
        self.reset_hierarchy()
