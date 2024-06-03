#createApp.py
#Made on 17/05/2024
#Contributed by Thijs Groeneweg and Bryan Owee
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#Builds the app file for macOS
#TODO: Update description


import os
import subprocess

def build_macos_app(filepath):
    try:
        # PyInstaller command with specified parameters
        command = [
            'pyinstaller',
            '-y',
            '--onefile',
            '--windowed',
            '--name', os.path.splitext(os.path.basename(filepath))[0],
            '--add-data', f'{filepath}:.',
            '--add-data', './PythonScript/openActivityBrowser.sh:.',
            filepath
        ]

        # Execute the PyInstaller command
        subprocess.run(command, check=True)
        print(f"Successfully built {filepath}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    directory = '/Users/bryanowee/Documents/GitHub/SE2/activity-browser/ActivityBrowserInstaller/Combined/PythonScript'
    for filename in os.listdir(directory):
        if filename.endswith('.py'):
            full_path = os.path.join(directory, filename)
            build_macos_app(full_path)
