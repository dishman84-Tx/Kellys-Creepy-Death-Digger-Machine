; Kelly's Creepy Death Digger Machine - Installer Script
; v1.3 - Randomized MP4 Loaders & High-Speed API

[Setup]
AppId={{A1B2C3D4-E5F6-4G7H-8I9J-K0L1M2N3O4P5}
AppName=Kelly's Creepy Death Digger Machine
AppVersion=1.3
AppPublisher=Kelly's Creepy Software
DefaultDirName={autopf}\KellysCreepyDeathDigger
DefaultGroupName=Kelly's Creepy Death Digger Machine
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=KellysCreepyDigger_v1.3_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Set the installer icon itself
SetupIconFile=C:\Users\jayde\Projects\Kellys-Creepy-Death-Digger-Machine\ui\assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Changed Flags to null so it's checked by default
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "C:\Users\jayde\Projects\Kellys-Creepy-Death-Digger-Machine\dist\KellysCreepyDeathDigger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Added IconFilename to explicitly point to the ico file for the shortcuts
Name: "{group}\Kelly's Creepy Death Digger Machine"; Filename: "{app}\KellysCreepyDeathDigger.exe"; IconFilename: "{app}\_internal\ui\assets\icon.ico"
Name: "{group}\{cm:UninstallProgram,Kelly's Creepy Death Digger Machine}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Kelly's Creepy Death Digger Machine"; Filename: "{app}\KellysCreepyDeathDigger.exe"; Tasks: desktopicon; IconFilename: "{app}\_internal\ui\assets\icon.ico"

[Run]
Filename: "{app}\KellysCreepyDeathDigger.exe"; Description: "{cm:LaunchProgram,Kelly's Creepy Death Digger Machine}"; Flags: nowait postinstall skipifsilent
