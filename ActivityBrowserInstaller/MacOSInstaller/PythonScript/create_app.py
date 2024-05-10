import subprocess

def build_macos_app():
    try:
        # PyInstaller command with specified parameters
        command = [
            'pyinstaller',
            '-y',
            '--onefile',
            '--windowed',
            '--name', 'ActivityBrowser',
            '--add-data=./openActivityBrowser.py:.',
            '--add-data=./openActivityBrowser.sh:.',
            'openActivityBrowser.py'
        ]

        # Execute the PyInstaller command
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    build_macos_app()
