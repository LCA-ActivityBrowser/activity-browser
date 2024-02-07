# -*- coding: utf-8 -*-
from .activity import ActivityController
from .exchange import ExchangeController
from .database import DatabaseController
from .parameter import ParameterController
from .project import ProjectController
from .impact_category import ImpactCategoryController
from .calculation_setup import CalculationSetupController
from .utilities import UtilitiesController
from .plugin import PluginController

controllers = {
    "activity_controller": ActivityController,
    "exchange_controller": ExchangeController,
    "database_controller": DatabaseController,
    "parameter_controller": ParameterController,
    "plugin_controller": PluginController,
    "project_controller": ProjectController,
    "cs_controller": CalculationSetupController,
    "ia_controller": ImpactCategoryController,
    "utils_controller": UtilitiesController,
}
