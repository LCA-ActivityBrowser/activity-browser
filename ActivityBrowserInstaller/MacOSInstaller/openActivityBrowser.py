import subprocess

def run_activity_browser():
    """Run the 'openActivityBrowser.sh' script."""
    subprocess.run("./openActivityBrowser.sh", shell=True)

if __name__ == "__main__":
    run_activity_browser()