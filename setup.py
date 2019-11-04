# -*- coding: utf-8 -*-
import os
from setuptools import setup

packages = []
root_dir = os.path.dirname(__file__)
if root_dir:
    os.chdir(root_dir)

for dirpath, dirnames, filenames in os.walk('activity_browser'):
    # Ignore dirnames that start with '.'
    if '__init__.py' in filenames:
        pkg = dirpath.replace(os.path.sep, '.')
        if os.path.altsep:
            pkg = pkg.replace(os.path.altsep, '.')
        packages.append(pkg)

setup(
    name='activity-browser',
    version="2.4.0",
    packages=packages,
    include_package_data=True,
    author="Bernhard Steubing",
    author_email="b.steubing@cml.leidenuniv.nl",
    license=open('LICENSE.txt').read(),
    install_requires=[], # dependency management in conda recipe
    url="https://github.com/LCA-ActivityBrowser/activity-browser",
    long_description=open('README.md').read(),
    description='A graphical user interface for brightway2',
    entry_points={
        'console_scripts': [
            'activity-browser = activity_browser.app:run_activity_browser',
        ]
    },
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],)
