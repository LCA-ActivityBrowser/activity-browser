"""
- openActivityBrowser.py
- Date of File Creation: 10/05/2024
- Contributors: Thijs Groeneweg & Ruben Visser & Bryan Owee
- Date and Author of Last Modification: 10/05/2024 - Thijs Groeneweg
- Synopsis of the File's purpose:
    This script runs the 'openActivityBrowser.sh' script which activates the 'ab' Conda environment 
    and starts the 'activity-browser' application.
"""

import subprocess

def runActivityBrowser():
    """Run the 'openActivityBrowser.sh' script."""
    subprocess.run("./openActivityBrowser.sh", shell=True)

if __name__ == "__main__":
    runActivityBrowser()