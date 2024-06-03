<!-- 
README.md       
Made on 11/03/2024         
Contributed by Arian Farzad, Ruben Visser, Thijs Groeneweg and Bryan Owee
Documented by Arian Farzad
Last edited on 03/06/2024

Contains the README of the ABInstaller&Updater
-->

# Activity Browser Installer ✨
<img src="https://user-images.githubusercontent.com/33026150/54299977-47a9f680-45bc-11e9-81c6-b99462f84d0b.png" width=100%/>

Welcome to the Activity Browser Installer & Updater, ABInstaller for short.
This is a project from the Unpaid Interns team contributing to the main AB Project.
You can find the repository for the Collaborative Activity Browser Project of ours [here](https://github.com/ludev-nl/2024-11-Activity-Browser/).

## The Project

The ABInstaller was a project to build a proper installer and installer for the '[the Activity Browser](https://github.com/LCA-ActivityBrowser/activity-browser)'.
This was a much-desired feature, as beforehand one would have to manually install the AB through Conda.
The ABInstaller allows the generation of .exe or .app files that can be distributed to allow users an easier installation with the click of a few buttons.
Outlined in this document will be the guidelines on how to generate such files.

## Installation

### Windows

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
      - `"...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\{#appExeName}"; DestDir: "{app}";`
      - `"...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_uninstaller.exe"; DestDir: "{app}"; Flags: ignoreversion`
      - `"...\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_installer.exe"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall`
      - `"...\ActivityBrowserInstaller\WindowsInstaller\[FILENAME].tar.gz"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall`
      - `"...\ActivityBrowserInstaller\WindowsInstaller\icon.ico" ; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall`
    - Also change the appVersion value at the top of this file to the current version.
	- Click the run button or press F9 to compile the installer.
   - This generates the ActivityBrowserSetup.exe in the output file.

     This file can now simply be distributed and is ready for use.

### macOS

1. Navigate to the "AB installer" directory to find all necessary files for creating the installer.
   - This directory can be found in …\activity-browser\ActivityBrowserInstaller

2. To create the installer the AB Conda Environment needs to be present on the current computer:
   - Run the createApp.py file to create the AB application
   - In the createApp.py file, the variable directory may need to change to where the folder "PythonScript" is located.
   - An example of this directory change: '/Users/peterwillem02/Documents/GitHub/SE2/activity-browser/ActivityBrowserInstaller/Combined/PythonScript'

- Conda has to be installed on path
- The Activity Browser can be run using chmod +x <ActiviBrowser.app filename>. It needs to be run as chmod, because it needs permission to download files.

## The 'Unpaid Interns'

The Unpaid Interns is a group of six students from Universiteit Leiden.
They worked together on the ABInstaller as a group project for their Software Engineering course.

The team consists out of:
- [Thijs Groeneweg](https://github.com/ThijsGroeneweg) - Product Owner
- [Arian Farzad](https://github.com/ThisIsSomeone) - Head of Documentation & Scrum Master
- [Hannah Gibb](https://github.com/hjgibb) - Head of Communication
- [Michiel van der Bijl](https://github.com/michiel9797) - Scribe
- [Ruben Visser](https://github.com/rcjvisserleiden) - Head of Testing
- [Bryan Owee](https://github.com/BryanOwee) - Developer

This project was in due part possible to their mentor.
- [Sjors Holtrop](https://github.com/sholtrop)
