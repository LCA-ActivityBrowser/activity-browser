# -*- coding: utf-8 -*-
import os
from setuptools import setup

version = os.environ.get("VERSION") or os.environ.get("PKG_VERSION")
if not version:
    version = os.environ.get("GIT_DESCRIBE_TAG", "0.0.0")
    if "-" in version:
        versions = version.split("-")
        version = "{}.post{}".format(versions[0], versions[1])

setup(
    version=version,
    packages=["activity_browser"],
    license=open("LICENSE.txt").read(),
    include_package_data=True,
)
