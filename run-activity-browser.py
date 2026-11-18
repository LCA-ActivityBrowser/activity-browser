# -*- coding: utf-8 -*-
"""Entry script for Activity Browser (also the PyInstaller Analysis entry).

On Windows frozen builds, ``multiprocessing`` child processes re-exec this
script. ``freeze_support()`` must run in the ``__main__`` block so workers
exit before the GUI starts; otherwise every Pool worker launches a new
Activity Browser window.
"""

if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    from activity_browser import run_activity_browser

    run_activity_browser()
