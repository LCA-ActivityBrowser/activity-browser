from .database_explorer import DatabaseExplorerPane
from .database_products import DatabaseProductsPane
from .project_manager import ProjectManagerPane
from .databases import DatabasesPane
from .impact_categories import ImpactCategoriesPane
from .calculation_setups import CalculationSetupsPane


registered_panes = [
    DatabaseExplorerPane,
    DatabaseProductsPane,
    ProjectManagerPane,
    DatabasesPane,
    ImpactCategoriesPane,
    CalculationSetupsPane,
]

shown_panes = [
    DatabasesPane,
    ImpactCategoriesPane,
    CalculationSetupsPane,
]

hidden_panes = [
    ProjectManagerPane,
]

default_panes = shown_panes + hidden_panes
