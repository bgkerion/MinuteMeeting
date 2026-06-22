; Inno Setup script per MinuteMeeting
; Versione di Inno Setup richiesta: 6.x
;
; Eseguire DOPO aver costruito il bundle con PyInstaller:
;   poetry run python scripts/build.py
; poi:
;   iscc installer\minute_meeting.iss
;
; Output: dist\MinuteMeeting-Setup-0.1.0.exe

#define AppName      "MinuteMeeting"
#define AppVersion   "0.1.0"
#define AppPublisher "Paolo Bellagente"
#define AppExeName   "MinuteMeeting.exe"
#define BundleDir    "..\dist\MinuteMeeting"

[Setup]
AppId={{F3A2C8D1-4B5E-4F6A-9C2D-1E7B8F0A3D5C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/pbellagente/MinuteMeeting
AppSupportURL=https://github.com/pbellagente/MinuteMeeting/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Il bundle è già grande (~1.5-2 GB): usa lzma con compressione veloce
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
; Solo a 64-bit — torch e ctranslate2 non hanno build a 32-bit
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
OutputDir=..\dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
; UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "italian";  MessagesFile: "compiler:Languages\Italian.isl"
Name: "english";  MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copia tutto il bundle onedir generato da PyInstaller
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";        Filename: "{app}\{#AppExeName}"
Name: "{group}\Disinstalla {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "Avvia {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Rimuovi la cache modelli lasciata dall'app (opzionale — commentare per conservarla)
; Type: filesandordirs; Name: "{localappdata}\.cache\minute_meeting"
; Type: filesandordirs; Name: "{localappdata}\.cache\whisperx"
