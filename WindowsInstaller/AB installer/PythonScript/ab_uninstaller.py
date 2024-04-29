import shutil
import os

current_directory = os.getcwd()
directory_path = os.path.join(current_directory, "ActivityBrowserEnvironment")

try:
    shutil.rmtree(directory_path)
    print(f"Directory '{directory_path}' successfully removed.")
except FileNotFoundError:
    print(f"Directory '{directory_path}' not found.")
