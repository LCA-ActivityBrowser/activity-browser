from setuptools import setup
import os

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
    version="1.1",
    packages=packages,
    package_data={'lca_activity_browser': [
        "icons/*.png",
        "icons/context/*.png",
        "icons/pony/*.png",
        "icons/metaprocess/*.png",
        "HTML/*.html",
        "HTML/dagre/*.js",
        "HTML/d3/*.js",
    ]},
    author="Bernhard Steubing",
    author_email="steubing.bernhard@gmail.com",
    license=open('LICENSE.txt').read(),
    install_requires=[
        "arrow",
        "brightway2",
        "eight",
        "jinja2",
        "matplotlib",
        "networkx",
        # "PyQt4",  # BW3TODO: How to specify?
    ],
    url="https://bitbucket.org/bsteubing/activity-browser",
    long_description=open('README.md').read(),
    description=('GUI for LCA software and metaprocesses'),
    entry_points = {
        'console_scripts': [
            'activity-browser-old = lca_activity_browser.bin.activity_browser:run_activity_browser',
            'activity-browser = lca_activity_browser.app:run_activity_browser',
        ]
    },
    classifiers=[
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        # 'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],)
