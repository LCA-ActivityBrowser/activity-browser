# -*- coding: utf-8 -*-
from importlib import metadata
from os import environ
import subprocess
import requests


def check_ab_update() -> bool:
    ab_url = "https://api.anaconda.org/package/mrvisscher/activity-browser-beta"
    ab_response = requests.get(ab_url)
    ab_current = metadata.version("activity_browser")

    if ab_response.status_code != 200:
        print("Could not fetch latest activity browser beta version")
        return False

    print(f"activity_browser_beta: {ab_current} x {ab_response.json()['latest_version']}")

    if ab_current == "0.0.0" or ab_current == ab_response.json()['latest_version']:
        return False
    return True


def check_bf_update() -> bool:
    bf_url = "https://api.anaconda.org/package/mrvisscher/bw_functional"
    bf_response = requests.get(bf_url)
    bf_current = metadata.version("bw_functional")
    if bf_response.status_code != 200:
        print("Could not fetch latest brightway functional version")
        return False

    print(f"bw_functional:         {bf_current} x {bf_response.json()['latest_version']}")

    if bf_current == bf_response.json()['latest_version']:
        return False
    return True


def run():
    from activity_browser import run_activity_browser
    print("Launching the Activity Browser")
    run_activity_browser()


if __name__ == '__main__':
    print("Activity Browser 3 Beta Release")
    print("______________________________________")
    ab = check_ab_update()
    bf = check_bf_update()
    print("______________________________________")
    if bf and environ.get("CONDA_DEFAULT_ENV"):
        print("Updating bw_functional")
        proc = subprocess.run(["conda", "update", "bw_functional"])
        if proc.returncode != 0:
            print("Update failed, try updating manually")
    if ab and environ.get("CONDA_DEFAULT_ENV"):
        print("Updating activity-browser-beta")
        proc = subprocess.run(["conda", "update", "activity-browser-beta"])
        if proc.returncode != 0:
            print("Update failed, try updating manually")

    run()
