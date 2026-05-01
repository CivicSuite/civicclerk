#ifndef MyAppVersion
  #error MyAppVersion must be supplied with /DMyAppVersion=<semver>
#endif

#define MyAppName "CivicClerk"
#define MyAppPublisher "CivicSuite"
#define MyAppExeName "install.ps1"

[Setup]
AppId={{7B10E5DE-4329-4A18-AB31-33A9A93F5EA1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CivicSuite\CivicClerk
DefaultGroupName=CivicSuite\CivicClerk
DisableProgramGroupPage=yes
OutputDir=build
OutputBaseFilename=CivicClerk-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName=CivicClerk

[Files]
Source: "..\..\install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docker-compose.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\.dockerignore"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\Dockerfile.backend"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\Dockerfile.frontend"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\USER-MANUAL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE-CODE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE-DOCS"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\civicclerk\*"; DestDir: "{app}\civicclerk"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
Source: "..\..\prompts\*"; DestDir: "{app}\prompts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\docker\*"; DestDir: "{app}\docker"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
Source: "..\..\frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules\*,dist\*,.vite\*"
Source: "README.md"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "prereq-check.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "launch-install.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "launch-start.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion

[Icons]
Name: "{group}\Start CivicClerk"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\windows\launch-start.ps1"""; WorkingDir: "{app}"
Name: "{group}\Install or Repair CivicClerk"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\windows\launch-install.ps1"""; WorkingDir: "{app}"
Name: "{group}\Stop CivicClerk"; Filename: "docker"; Parameters: "compose down"; WorkingDir: "{app}"
Name: "{group}\Open CivicClerk Staff App"; Filename: "http://127.0.0.1:8080/"
Name: "{group}\Installer README"; Filename: "{app}\installer\windows\README.md"
Name: "{group}\Uninstall CivicClerk"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Start CivicClerk"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\windows\launch-start.ps1"""; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\windows\launch-install.ps1"""; WorkingDir: "{app}"; Description: "Install or repair CivicClerk now"; Flags: postinstall skipifsilent

[UninstallRun]
Filename: "docker"; Parameters: "compose down"; WorkingDir: "{app}"; Flags: runhidden; RunOnceId: "StopCivicClerkStack"

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox(
    'Uninstalling CivicClerk will stop the Docker Compose stack and remove installed source files. Docker volumes are preserved so meeting data is not erased accidentally. To intentionally delete local rehearsal data, run docker compose down -v from the install directory.',
    mbInformation,
    MB_OKCANCEL
  ) = IDOK;
end;
