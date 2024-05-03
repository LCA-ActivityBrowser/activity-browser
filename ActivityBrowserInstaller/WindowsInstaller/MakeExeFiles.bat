@echo off
setlocal enabledelayedexpansion

rem Ask user to input the directory containing Python script files
set /p python_script_dir="Enter the directory containing Python script files: "

rem Navigate to the specified directory
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
