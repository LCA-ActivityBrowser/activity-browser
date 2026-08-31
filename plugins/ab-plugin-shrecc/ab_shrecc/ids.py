# -*- coding: utf-8 -*-
"""Contribution ids (namespaced as ``plugin_id.local``)."""

PLUGIN_ID = "ab_shrecc"

PAGE = f"{PLUGIN_ID}.page"
SHOW_PAGE = f"{PLUGIN_ID}.show_page"
SETTINGS = f"{PLUGIN_ID}.settings"

STAGE_CONFIGURE = "configure"
STAGE_CREATE_INSPECT = "create_inspect"
STAGE_WRITE = "write"

STAGE_LABELS = {
    STAGE_CONFIGURE: "1 Configure",
    STAGE_CREATE_INSPECT: "2 Create & inspect",
    STAGE_WRITE: "3 Write",
}
