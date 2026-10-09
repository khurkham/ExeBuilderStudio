; Install EXE Builder Studio only. Never include a developer private key in a Setup.
[Setup]
AppId={{D8E2ADBD-AD56-4445-A82F-7DA1EFA564B6}
AppName=EXE Builder Studio
AppVersion=1.0
AppPublisher=Khurkham Langkhur
DefaultDirName={localappdata}\Programs\ExeBuilderStudio
DefaultGroupName=EXE Builder Studio
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=ExeBuilderStudio_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\ExeBuilderStudio.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\ExeBuilderStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EXE Builder Studio"; Filename: "{app}\ExeBuilderStudio.exe"
Name: "{userdesktop}\EXE Builder Studio"; Filename: "{app}\ExeBuilderStudio.exe"; Tasks: desktopicon

[Run]
; This creates a TEST signing identity for the builder's current user, not a trusted root.
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\Ensure-Certificate.ps1"" -Quiet"; Flags: runhidden waituntilterminated
Filename: "{app}\ExeBuilderStudio.exe"; Description: "Launch EXE Builder Studio"; Flags: nowait postinstall skipifsilent
