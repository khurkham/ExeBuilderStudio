; Install EXE Builder Studio. Offline tool payloads are publisher-supplied and validated before build.
#ifndef InstallerMode
  #define InstallerMode "Standard"
#endif
[Setup]
AppId={{D8E2ADBD-AD56-4445-A82F-7DA1EFA564B6}
AppName=EXE Builder Studio
AppVersion=1.2
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
Name: "{group}\EXE Builder Studio"; Filename: "{app}\ExeBuilderStudio.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\EXE Builder Studio"; Filename: "{app}\ExeBuilderStudio.exe"; WorkingDir: "{app}"; Tasks: desktopicon
