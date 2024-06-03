rem CreateABTarbal.bat
rem Made on 24/05/2024
rem Contributed by Thijs Groeneweg
rem Documented by Arian Farzad
rem Last edited on 03/06/2024 by Arian Farzad

rem Packs the AB environment into a tarball
rem TODO: Update description

@echo off

rem Prompt user for environment name
set /p environmentName=Enter the name of the Activity Browser conda environment: 

rem Build the conda pack command with user input
set "packCommand=conda-pack --name %environmentName%"

rem Execute the conda pack command
echo Executing: %packCommand%

%packCommand%

rem Pause for user to see output (optional)
pause
