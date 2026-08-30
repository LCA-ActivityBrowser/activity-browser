# -*- coding: utf-8 -*-
"""Shared Brightway-backed status text for the example plugin."""


def current_project_label() -> str:
    import bw2data as bd

    return bd.projects.current or "(none)"
