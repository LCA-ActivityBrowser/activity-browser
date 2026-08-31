# -*- coding: utf-8 -*-
"""Contribution ids (namespaced as ``plugin_id.local``)."""

PLUGIN_ID = "ab_shrecc"

PAGE = f"{PLUGIN_ID}.page"
SHOW_PAGE = f"{PLUGIN_ID}.show_page"
SETTINGS = f"{PLUGIN_ID}.settings"

STAGE_CONFIGURE = "configure"
STAGE_INSPECT = "inspect"
STAGE_WRITE = "write"

# Back-compat alias for older imports/tests
STAGE_CREATE_INSPECT = STAGE_INSPECT

STAGE_LABELS = {
    STAGE_CONFIGURE: "1 Configure",
    STAGE_INSPECT: "2 Inspect",
    STAGE_WRITE: "3 Write",
}
