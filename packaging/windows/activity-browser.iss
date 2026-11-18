; Inno Setup script for Activity Browser (Windows x64).
; Pass version at compile time: iscc /DMyAppVersion=YYYYMMDD-abcdef0 activity-browser.iss

#ifndef MyAppVersion
  #define MyAppVersion "dev"
#endif

#define MyAppName "Activity Browser"
#define MyAppPublisher "Activity Browser contributors"
#define MyAppURL "https://github.com/LCA-ActivityBrowser/activity-browser"
#define MyAppExeName "activity-browser.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-4789-ABCD-ACTIVITYBROWSER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE.txt
OutputDir=..\..\dist\installers
OutputBaseFilename=ActivityBrowser-{#MyAppVersion}-windows-x64-setup
SetupIconFile=..\..\activity_browser\static\icons\main\activitybrowser.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\activity-browser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\ActivityBrowser-{#MyAppVersion}-windows-x64-dependencies.txt"; DestDir: "{app}"; DestName: "dependencies.txt"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
