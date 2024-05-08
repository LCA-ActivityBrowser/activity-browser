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
#define PascalScripting

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
OutputBaseFilename=ActivityBrowser-{#appVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#installerIcon}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_uninstaller.exe"; DestDir: "{app}"; Flags: ignoreversion; AfterInstall: RunUninstaller
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ab_installer.exe"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\ActivityBrowser.tar.gz"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\icon.ico" ; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ActivityBrowser Updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\thijs\Documents\activity-browser-installer\ActivityBrowserInstaller\WindowsInstaller\PythonScript\dist\ActivityBrowser.exe"; DestDir: "{app}"; \
DestName: "ActivityBrowser-{#AppVersion}.exe"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Registry]
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#appAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}"; ValueType: string; ValueName: ""; ValueData: "{#appAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#appExeName},0"
Root: HKA; Subkey: "Software\Classes\{#appAssocExt}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#appExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#appExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""

[Icons]
Name: "{group}\{#appName}"; Filename: "{app}\ActivityBrowser-{#appVersion}.exe"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#appName}}"; Filename: "{uninstallexe}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#appName}"; Filename: "{app}\{#appExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"


[Run]
Filename: "{app}\{#condaEnvCreator}"; Flags: runhidden ; StatusMsg: "Installing the Conda Environment"
Filename: "{app}\ActivityBrowser-{#appVersion}.exe"; Description: "{cm:LaunchProgram,{#StringChange(appName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#condaEnvDeletor}"; Flags: runhidden

[Code]
procedure RunUninstaller;
var
  ResultCode: Integer;
begin
  WizardForm.FilenameLabel.Caption := 'Removing ActivityBrowser environment and startup file if they exist...';
  if not Exec(ExpandConstant('{app}\{#condaEnvDeletor}'), '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Failed to run ' + '{#condaEnvDeletor}' + '. The error code was ' + IntToStr(ResultCode) + '.', mbError, MB_OK);
  end;
end;
