"""
ActivityBrowserEnvironmentRemover.py
Date of File Creation: 10/05/2024
Contributors: Thijs Groeneweg
Date and Author of Last Modification: 10/05/2024 - Thijs Groeneweg
Synopsis of the File's purpose: This script removes the 'ab' Conda environment.
"""

import subprocess

def removeActivityBrowserEnvironment():
    """Remove the 'ab' Conda environment."""
    try:
        # Define the name of the Conda environment to remove
        environment_name = "ab"

        # Remove the Conda environment
        subprocess.run(["conda", "env", "remove", "--name", environment_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    except FileNotFoundError:
        print("Error: The command does not exist or is not accessible.")


if __name__ == "__main__":
    removeActivityBrowserEnvironment()