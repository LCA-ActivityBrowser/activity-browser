# -*- coding: utf-8 -*-
import os
from setuptools import setup

if "VERSION" in os.environ:
    version = os.environ["VERSION"]
elif "PKG_VERSION" in os.environ:
    version = os.environ["PKG_VERSION"]
else:
    version = os.environ.get("GIT_DESCRIBE_TAG", "0.0.0")
    if "-" in version:
        versions = version.split("-")
        version = "{}.post{}".format(versions[0], versions[1])

setup(
    version=version,
    packages=["activity_browser", "activity_browser_beta"],
    license=open("LICENSE.txt").read(),
    include_package_data=True,
)
