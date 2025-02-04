# -*- coding: utf-8 -*-
from importlib import reload
import activity_browser as ab
import subprocess
import requests

if __name__ == '__main__':
    url = "https://api.anaconda.org/package/mrvisscher/activity-browser-beta"
    response = requests.get(url)

    if response.status_code == 200:
        print("Could not fetch latest beta version")

    elif ab.version != "0.0.0" and ab.version != response.json()['latest_version']:
        print("Your Activity Browser Beta is outdated")
        print("______________________________________")
        print(f"Your version:     {ab.version}")
        print(f"Latest version:   {response.json()['latest_version']}")
        print("______________________________________")
        print("update by using `conda update activity-browser-beta`")
        proc = subprocess.run(["conda", "update", "activity-browser-beta"])

        if proc.returncode != 0:
            print("Update failed, try updating manually")
        else:
            reload(ab)
            print(f"Update successful, launching ab {ab.version}")

    ab.run_activity_browser()
