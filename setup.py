import os
from setuptools import setup

packages = []
root_dir = os.path.dirname(__file__)
if root_dir:
    os.chdir(root_dir)

for dirpath, dirnames, filenames in os.walk('lca_activity_browser'):
    # Ignore dirnames that start with '.'
    if '__init__.py' in filenames:
        pkg = dirpath.replace(os.path.sep, '.')
        if os.path.altsep:
            pkg = pkg.replace(os.path.altsep, '.')
        packages.append(pkg)

setup(
    name='lca_activity_browser',
    version="2.1.dev",
    packages=packages,
    package_data={'lca_activity_browser': [
        "icons/context/*.png",
        "icons/pony/*.png",
        "icons/metaprocess/*.png",
        "icons/main/*.png"
    ]},
    author="Adrian Haas",
    author_email="haasad@student.ethz.ch",
    license=open('LICENSE.txt').read(),
    install_requires=['brightway2', 'pyqt5', 'requests-oauthlib', 'seaborn', 'arrow'],
    url="https://github.com/haasad/activity-browser",
    long_description=open('README.md').read(),
    description=('Brightway2 GUI'),
    entry_points = {
        'console_scripts': [
            'activity-browser = lca_activity_browser.app:run_activity_browser',
        ]
    },
    classifiers=[
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],)
