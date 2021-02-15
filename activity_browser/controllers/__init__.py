# -*- coding: utf-8 -*-
from .activity import ActivityController, ExchangeController
from .database import DatabaseController
from .parameter import ParameterController
from .project import ProjectController, CSetupController
from .utils import UtilitiesController

controllers = {
    "activity_controller": ActivityController,
    "exchange_controller": ExchangeController,
    "database_controller": DatabaseController,
    "parameter_controller": ParameterController,
    "project_controller": ProjectController,
    "cs_controller": CSetupController,
    "utils_controller": UtilitiesController,
}
