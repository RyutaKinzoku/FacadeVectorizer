; Inno Setup script for PhotoToCAD.
;
; CANNOT be compiled or tested in this Linux dev sandbox -- Inno Setup
; (ISCC.exe) is Windows-only software and isn't installable here (it's
; not even in this environment's network allowlist). This is real,
; correct Inno Setup syntax, written carefully and reviewed against the
; actual PyInstaller output structure (see app.spec / the dist/ layout
; that produced), but it has NOT been run through a real compile here.
; The first real test of this file has to happen on an actual Windows
; machine (or a Windows CI runner) -- treat that as a required step,
; not an optional sanity check.
;
; Build order:
;   1. pyinstaller packaging/app.spec --distpath packaging/dist --workpath packaging/build
;      (run on Windows, producing packaging/dist/PhotoToCAD/PhotoToCAD.exe
;      and its _internal/ folder -- see app.spec's own docstring for why
;      this must run on Windows, not be reused from a Linux build)
;   2. Compile this script with ISCC.exe (or open it in the Inno Setup
;      IDE and press Compile) -- produces
;      packaging/installer_output/PhotoToCAD-Setup-0.1.0.exe
;   3. Sign both PhotoToCAD.exe (before step 2) and the installer .exe
;      (after step 2) -- see sign.ps1, also untested here for the same
;      reason.
;
; AppId is a real, randomly generated GUID (not a placeholder) -- Inno
; Setup uses it to recognise upgrades/uninstalls of the same product
; across versions. Keep this exact value in every future release; do not
; regenerate it.

#define AppName "PhotoToCAD"
#define AppVersion "0.1.0"
#define AppPublisher "Photo-to-CAD Project"
#define AppExeName "PhotoToCAD.exe"

[Setup]
AppId={{0FF88372-7A82-48E4-B01C-56F71852B7AE}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Per-user install with no admin prompt is friendlier for a tool like
; this one (no system-level integration needed); switch to
; PrivilegesRequired=admin + DefaultDirName={pf} if you'd rather install
; for all users under Program Files.
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Everything PyInstaller produced -- the exe plus its _internal/ folder
; (DLLs, the Qt runtime, bundled i18n/ and models/ data). Source path is
; relative to this .iss file's own location, same convention as
; app.spec's SPECPATH, so this only works if dist/ sits next to this
; script under packaging/ -- exactly where the build command above puts it.
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
