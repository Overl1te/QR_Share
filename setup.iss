#define MyAppName "QR_Share"
#define MyAppVersion "1.0"
#define MyAppPublisher "Overl1te"
#define MyAppURL "https://github.com/Overl1te/QR_Share"
#define MyAppExeName "main.exe"

[Setup]
AppId={{11701B4F-FCE5-402B-822D-F52FA7B0C0D4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=QR_Share_Setup
SolidCompression=yes
WizardStyle=modern dynamic
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKA; Subkey: "Software\Classes\*\shell\QR Share"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\*\shell\QR Share"; ValueType: string; ValueName: "Icon"; ValueData: "imageres.dll,-1020"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\*\shell\QR Share\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey