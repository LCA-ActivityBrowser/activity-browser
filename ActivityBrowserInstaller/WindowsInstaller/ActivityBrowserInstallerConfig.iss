#define appName "Activity Browser"
#define appVersion "2.9.7"
#define appPublisher "Bernhard Steubing"
#define appURL "https://github.com/LCA-ActivityBrowser/activity-browser"
#define appExeName "ActivityBrowser.exe"
#define condaEnvCreator "ab_installer.exe"
#define condaEnvDeletor "ab_uninstaller.exe"
#define installerIcon "icon.ico"
#define appAssocName AppName + ""
#define appAssocExt ".myp"
#define appAssocKey StringChange(appAssocName, " ", "") + appAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; Keep the AppId consistent for each version of the ActivityBrowser
AppId={{D6D31A57-0072-4EBB-B48D-4365FF1F2361}
AppName={#appName}
AppVersion={#appVersion}
AppPublisher={#appPublisher}
AppPublisherURL={#appURL}
AppSupportURL={#appURL}
AppUpdatesURL={#appURL}
DefaultDirName={autopf}\{#appName}
ChangesAssociations=yes
DefaultGroupName={#appName}
AllowNoIcons=yes
OutputBaseFilename=ActivityBrowserSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#installerIcon}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\rcjvi\Documents\activity-browser\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\{#appExeName}"; DestDir: "{app}";
Source: "C:\Users\rcjvi\Documents\activity-browser\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_uninstaller.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\rcjvi\Documents\activity-browser\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_installer.exe"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "C:\Users\rcjvi\Documents\activity-browser\ActivityBrowserInstaller\WindowsInstaller\ab.tar.gz"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Registry]
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#appAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}"; ValueType: string; ValueName: ""; ValueData: "{#appAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#appExeName},0"
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#appExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#appExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""

[Icons]
Name: "{group}\{#appName}"; Filename: "{app}\{#appExeName}"
Name: "{group}\{cm:UninstallProgram,{#appName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#appName}"; Filename: "{app}\{#appExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#condaEnvCreator}"; Flags: runhidden ; StatusMsg: "Installing the Conda Environment"
Filename: "{app}\{#appExeName}"; Description: "{cm:LaunchProgram,{#StringChange(appName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#condaEnvDeletor}"; Flags: runhidden
