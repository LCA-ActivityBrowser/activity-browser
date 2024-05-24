# AB Installer README WINDOWS

This README provides instructions for installing the Activity Browser (AB) using the provided installer.

## Installation Steps

1. Navigate to the "AB installer" directory to find all necessary files for creating the installer.
   - This directory can be found in …\activity-browser\ActivityBrowserInstaller\WindowsInstaller

2. To create the installer the AB Conda Environment needs to be present on the current computer:
   - Create the Activity Browser Conda environment using Conda. 
   - The guide how to create this can be found on: https://github.com/LCA-ActivityBrowser/activity-browser?tab=readme-ov-file#installation

3. Create the AB Tarball:
   - Run the `CreateABTarball.bat` script and provide the name of the AB Conda environment when prompted (e.g., "ab"). This tarball includes the whole Conda environment to create the installer.

4. Generate Executable Files:
   - Execute the `MakeExeFiles.bat` script following the instruction to add the correct path.
   - This script generates installer, uninstaller, and Activity Browser executable files based on Python scripts.

5. Configure and Run Inno Setup Compiler to generate the ActivityBrowserSetup.exe file:
   - Install Inno Setup from the internet. You need this program to compile the setup file.
   - Run `ActivityBrowserInstallerConfig.iss` after making required modifications:
   	- Open the file and adjust the 4 lines under the "[Files]" section to have your own file paths.
      Only change the ... in the lines, except for the fourth line, also change the FILENAME of the tar.gz file:
      "...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\{#appExeName}"; DestDir: "{app}";
      "...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_uninstaller.exe"; DestDir: "{app}"; Flags: ignoreversion
      "...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_installer.exe"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
      "...\ActivityBrowserInstaller\WindowsInstaller\[FILENAME].tar.gz"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
      "...\ActivityBrowserInstaller\WindowsInstaller\icon.ico" ; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
    - Also change the appVersion value at the top of this file to the current version.
	- Click the run button or press F9 to compile the installer.
   - This generates the ActivityBrowserSetup.exe in the output file.

## Usage

- The generated `ActivityBrowserSetup.exe` installs the AB environment and copies the Conda environment.



# AB Installer README MacOS

This README provides instructions for installing the Activity Browser (AB) using the provided installer.

## Installation Steps

1. Navigate to the "AB installer" directory to find all necessary files for creating the installer.
   - This directory can be found in …\activity-browser\ActivityBrowserInstaller

2. To create the installer the AB Conda Environment needs to be present on the current computer:
   - Run the createApp.py file to create the AB application
   - In the createApp.py file, the variable directory may need to change to where the folder "PythonScript" is located.
   - An example of this directory change: '/Users/peterwillem02/Documents/GitHub/SE2/activity-browser/ActivityBrowserInstaller/Combined/PythonScript'

## Usage

- Conda has to be installed on path
