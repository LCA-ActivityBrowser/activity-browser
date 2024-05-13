"""
- ab_uninstaller.py
- Date of File Creation: 22/04/2024
- Contributors: Thijs Groeneweg & Ruben Visser
- Date and Author of Last Modification: 13/05/2024 - Thijs Groeneweg
- Synopsis of the File's purpose:
    This Python script first obtains the current working directory and then constructs a path for a directory named
    "ActivityBrowserEnvironment" within that directory. It then attempts to remove this directory using shutil.rmtree().
    If the directory is successfully removed, it prints a success message indicating the directory's removal.
    If the directory is not found, it prints a message indicating that the directory was not found.
"""

import subprocess

def removeCondaEnv(env_name: str):
    """
    Remove a conda environment.

    Args:
    - env_name: The name of the conda environment to remove.
    """
    try:
        subprocess.run(["conda", "env", "remove", "--name", env_name], check=True)
        print(f"Conda environment '{env_name}' successfully removed.")
    except subprocess.CalledProcessError:
        print(f"Failed to remove conda environment '{env_name}'.")

if __name__ == "__main__":
    removeCondaEnv("ab")