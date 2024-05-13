import os
import subprocess

def build_macos_app(filename):
    try:
        # PyInstaller command with specified parameters
        command = [
            'pyinstaller',
            '-y',
            '--onefile',
            '--windowed',
            '--name', filename,
            '--add-data=./' + filename + ':.',
            '--add-data=./openActivityBrowser.sh:.',
            filename
        ]

        # Execute the PyInstaller command
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    directory = '.'  # Replace with your directory
    for filename in os.listdir(directory):
        if filename.endswith('.py'):
            build_macos_app(filename)
