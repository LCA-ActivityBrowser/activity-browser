# -*- coding: utf-8 -*-
from activity_browser import run_activity_browser, version
import requests

if __name__ == '__main__':
    url = "https://api.anaconda.org/package/mrvisscher/activity-browser-beta"
    response = requests.get(url)

    if response.status_code == 200 and version != "0.0.0" and version != response.json()['latest_version']:
        print("Your Activity Browser Beta is outdated")
        print("______________________________________")
        print(f"Your version:     {version}")
        print(f"Latest version:   {response.json()['latest_version']}")
        print("______________________________________")
        print("update by using `conda update activity-browser-beta`")
        y = input("Press enter to exit...").lower().strip()
        if y not in ["no", "i refuse", "denied", "please no"]:
            exit()
        if y == "please no":
            print("How well mannered of you")

    run_activity_browser()
