@echo off
setlocal enabledelayedexpansion

rem Set the path to the directory containing Python script files
set "python_script_dir=C:\Users\rcjvi\OneDrive\Bureaublad\activity-browser\AB installer\PythonScript"

rem Navigate to the directory containing Python script files
cd /d "%python_script_dir%"

rem Loop through all Python files in the directory
for %%f in (*.py) do (
    rem Extract file name without extension
    set "filename=%%~nf"
    
    rem Run PyInstaller to create standalone executable with specified icon
    pyinstaller --onefile --icon=icon.ico "%%f"
    
    rem Rename the output executable to the original filename
    ren "dist\%%~nxf.exe" "!filename!.exe"
)

rem Clean up temporary build files
rmdir /s /q "build"
del "*.spec"
