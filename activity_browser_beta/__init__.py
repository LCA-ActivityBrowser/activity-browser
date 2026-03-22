# -*- coding: utf-8 -*-
from importlib import metadata
from os import environ
from conda import cli
import requests


def check_ab_update() -> bool:
    ab_url = "https://api.anaconda.org/package/mrvisscher/activity-browser-beta"
    ab_response = requests.get(ab_url)
    ab_current = metadata.version("activity_browser")

    if ab_response.status_code != 200:
        print("Could not fetch latest activity browser beta version")
        return False

    ab_latest = ab_response.json()['latest_version'].replace(".", "")

    print(f"activity_browser_beta: {ab_current} x {ab_latest}")

    if ab_current == "0.0.0" or ab_current == ab_latest:
        return False
    return True


def run():
    from activity_browser import run_activity_browser
    print("Launching the Activity Browser")
    run_activity_browser()


def run_activity_browser():
    print("Activity Browser 3 Beta Release")
    print("______________________________________")
    ab = check_ab_update()
    print("______________________________________")
    if ab and environ.get("CONDA_DEFAULT_ENV"):
        print("Updating activity-browser-beta")
        cli.main("update", "-c", "mrvisscher", "activity-browser-beta",)
    run()
