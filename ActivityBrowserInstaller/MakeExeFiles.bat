rem MakeExeFiles.bat
rem Made on 24/05/2024
rem Contributed by Thijs Groeneweg
rem Documented by Arian Farzad
rem Last edited on 03/06/2024 by Arian Farzad

rem Generates .exe files when called
rem TODO: Update description
 


@echo off
setlocal enabledelayedexpansion

rem Ask user to input the directory containing Python script files
set /p python_script_dir="Enter the directory containing Python script files: "

cd /d "%python_script_dir%"

rem Loop through all Python files in the directory
for %%f in (*.py) do (
    rem Extract file name without extension
    set "filename=%%~nf"
    
    if "!filename!"=="ActivityBrowser Updater" (
        rem Run PyInstaller to create standalone executable with specified icon and --uac-admin. The updater requires admin privileges to update the application files.
        pyinstaller --onefile --icon=icon.ico --uac-admin "%%f"
    ) else (
        rem Run PyInstaller to create standalone executable with specified icon
        pyinstaller --onefile --icon=icon.ico "%%f"
    )
    
    rem Rename the output executable to the original filename
    ren "dist\%%~nxf.exe" "!filename!.exe"
)

rem Clean up temporary build files
rmdir /s /q "build"
del "*.spec"