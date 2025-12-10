from .database_products import DatabaseProductsPane
from .databases import DatabasesPane
from .impact_categories import ImpactCategoriesPane
from .calculation_setups import CalculationSetupsPane

base_panes = {
    "Databases": DatabasesPane,
    "Impact Categories": ImpactCategoriesPane,
    "Calculation Setups": CalculationSetupsPane,
}
