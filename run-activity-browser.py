# -*- coding: utf-8 -*-
import logging

from activity_browser.logger import ABHandler

from activity_browser import run_activity_browser


logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)

run_activity_browser()