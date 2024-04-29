@echo off

rem Prompt user for environment name
set /p environmentName=Enter the name of the Activity Browser conda environment: 

rem Build the conda pack command with user input
set "packCommand=conda pack --name %environmentName%"

rem Execute the conda pack command
echo Executing: %packCommand%

%packCommand%

rem Pause for user to see output (optional)
pause
