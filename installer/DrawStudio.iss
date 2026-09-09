#ifndef MyAppVersion
#define MyAppVersion "1.0.142-rc1"
#endif

[Setup]
#ifdef SignRelease
SignTool=drawstudio
SignedUninstaller=yes
#endif
AppId={{6A4AD303-4F16-4ED7-A9AF-5B912352D83E}
AppName=Draw Studio
AppVersion={#MyAppVersion}
VersionInfoVersion=1.0.142.0
AppPublisher=Draw Studio
DefaultDirName={localappdata}\Programs\Draw Studio
DefaultGroupName=Draw Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=DrawStudio-{#MyAppVersion}-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Draw Studio {#MyAppVersion}
SetupLogging=yes
RestartIfNeededByRun=no
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\DrawStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Draw Studio"; Filename: "{app}\DrawStudio.exe"
Name: "{autodesktop}\Draw Studio"; Filename: "{app}\DrawStudio.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\DrawStudio.exe"; Description: "Launch Draw Studio"; Flags: nowait postinstall; Check: ShouldLaunchDrawStudio

[Code]
function HasCommandLineParam(const Value: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
  begin
    if CompareText(ParamStr(I), Value) = 0 then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function ShouldLaunchDrawStudio(): Boolean;
begin
  Result := (not WizardSilent) or HasCommandLineParam('/RELAUNCHDRAWSTUDIO');
end;
