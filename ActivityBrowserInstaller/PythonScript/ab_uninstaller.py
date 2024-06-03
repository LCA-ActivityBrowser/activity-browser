#ab_uninstaller.py
#Made on 22/04/2024
#Contributed by Thijs Groeneweg and Ruben Visser
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#This Python script first obtains the current working directory and then constructs a path for a directory named
#"ActivityBrowserEnvironment" within that directory. It then attempts to remove this directory using shutil.rmtree().
#If the directory is successfully removed, it prints a success message indicating the directory's removal.
#If the directory is not found, it prints a message indicating that the directory was not found.
#TODO: Update description

#Imports
import shutil
import os

def getActivityBrowserFilename() -> str:
        """
        Get the filename of the ActivityBrowser executable in the current directory.

        Returns:
        - str: The filename of the ActivityBrowser executable.
        """
        for filename in os.listdir("."):
            if filename.startswith("ActivityBrowser-"):
                return filename
        return None

if __name__ == "__main__":
    currentDirectory = os.getcwd()
    directoryPath = os.path.join(currentDirectory, "ActivityBrowserEnvironment")

    try:
        shutil.rmtree(directoryPath)
        print(f"Directory '{directoryPath}' successfully removed.")
    except FileNotFoundError:
        print(f"Directory '{directoryPath}' not found.")

    try:
        os.remove(getActivityBrowserFilename())
    except FileNotFoundError:
        print("ActivityBrowser file not found in the directory.")