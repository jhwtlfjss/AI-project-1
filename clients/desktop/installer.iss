#define MyAppName "AI Project 1"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "AI Project 1"
#define MyAppExeName "AI Project 1.exe"
#define MyAppIcon "..\..\assets\app_icon.ico"

[Setup]
AppId={{68D3B015-8DD8-4D75-A66B-5375C2F01686}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=AIProject1Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}\clients"; Flags: ignoreversion
Source: ".\README.md"; DestDir: "{app}\clients\desktop"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
