@echo off
setlocal enabledelayedexpansion

rem Ask user to input the directory containing Python script files
set /p python_script_dir="Enter the directory containing Python script files: "

cd /d "%python_script_dir%"

rem Loop through all Python files in the directory
for %%f in (*.py) do (
    rem Extract file name without extension
    set "filename=%%~nf"
    
    if "!filename!"=="Updater" (
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