#define MyAppName "OCR de Capturas"
#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif
#define MyAppExeName "OCR-Capturas.exe"

[Setup]
AppId={{B83435DE-F785-4EB7-9437-4834A8E8D94F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppName}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\instalador
OutputBaseFilename=OCR-Capturas-{#MyAppVersion}-instalador
SetupIconFile=ocr_capturas.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
AppMutex=OCR-Capturas-SingleInstance
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "iniciarcomwindows"; Description: "Iniciar o OCR de Capturas com o Windows"; GroupDescription: "Inicialização:"; Flags: unchecked

[Files]
Source: "..\dist\OCR-Capturas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LEIA-ME.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OCR de Capturas"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--painel"; Comment: "Abrir o painel de controle"
Name: "{group}\Leia-me"; Filename: "{app}\LEIA-ME.txt"
Name: "{group}\Desinstalar OCR de Capturas"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OCR de Capturas"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--painel"; Tasks: desktopicon
Name: "{userstartup}\OCR de Capturas"; Filename: "{app}\{#MyAppExeName}"; Tasks: iniciarcomwindows

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--painel"; Description: "Abrir o OCR de Capturas agora"; Flags: nowait postinstall skipifsilent
