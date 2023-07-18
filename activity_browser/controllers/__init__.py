# -*- coding: utf-8 -*-
from .activity import ActivityController, ExchangeController
from .database import DatabaseController
from .parameter import ParameterController
from .project import (
    ProjectController, CSetupController, ImpactCategoryController
)
from .utils import UtilitiesController
from .plugin import PluginController

controllers = {
    "activity_controller": ActivityController,
    "exchange_controller": ExchangeController,
    "database_controller": DatabaseController,
    "parameter_controller": ParameterController,
    "plugin_controller": PluginController,
    "project_controller": ProjectController,
    "cs_controller": CSetupController,
    "ia_controller": ImpactCategoryController,
    "utils_controller": UtilitiesController,
}
