import os
import subprocess

def openActivityBrowser():
    # Get the directory of the current script
    base_dir = os.path.dirname(__file__)

    # Construct the full path to the shell script
    script_path = os.path.join(base_dir, 'openActivityBrowser.sh')

    try:
        # Execute the shell script with shell=True
        subprocess.run([script_path], check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print(f"Error: The script '{script_path}' does not exist or is not accessible.")

if __name__ == "__main__":
    openActivityBrowser()
