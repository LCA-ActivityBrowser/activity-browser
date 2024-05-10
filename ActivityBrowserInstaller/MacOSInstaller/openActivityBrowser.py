import subprocess

def run_activity_browser():
    """Activate the 'ab' conda environment and run the 'activity-browser' command."""
    subprocess.run("conda activate ab && activity-browser", shell=True)

if __name__ == "__main__":
    run_activity_browser()