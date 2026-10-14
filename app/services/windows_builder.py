"""Prepare portable Windows build kits from Windows or macOS hosts.

The kit is compiled on Windows because native Windows installers cannot be
reliably cross-compiled by jpackage or PyInstaller from macOS.
"""
from __future__ import annotations
import re, shutil, tempfile, zipfile
# Prepare a temporary Windows build kit; the actual installer is built locally on Windows.
from pathlib import Path
from app.services.macos_builder import _safe_name, _copy_project


def create_windows_build_kit(*, kind: str, source: str, output: str, name: str, icon: str = "") -> Path:
    """Create a ZIP kit that builds a native Windows installer on Windows."""
    from app.services.icon_support import prepare_icon
    if kind not in {"java", "python"}:
        raise ValueError("Unknown Windows build type.")
    src = Path(source).expanduser().resolve() if source else None
    if not src or not src.exists():
        raise ValueError("Select a source JAR or Python project folder/file.")
    app_name = _safe_name(name)
    out_dir = Path(output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    kit_path = out_dir / f"{app_name}_Windows_Build_Kit.zip"
    if kit_path.exists():
        raise ValueError("The Windows build kit already exists. Choose another output folder or rename the app.")
    with tempfile.TemporaryDirectory(prefix="ebs_windows_kit_") as temp:
        root = Path(temp) / f"{app_name}_Windows_Build_Kit"
        source_dir = root / "source"; source_dir.mkdir(parents=True)
        resources = root / "resources"; resources.mkdir()
        icon_path = prepare_icon(icon, resources / "app.ico", "windows") if icon else None
        if kind == "java":
            if not src.is_file() or src.suffix.lower() != ".jar":
                raise ValueError("Select a Java .jar file.")
            shutil.copy2(src, source_dir / src.name)
            lib = src.parent / "lib"
            if lib.is_dir(): shutil.copytree(lib, source_dir / "lib", ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
            icon_arg = ' --icon "$Root\\resources\\app.ico"' if icon_path else ""
            script = f'''$ErrorActionPreference = "Stop"
# Build a native Windows EXE installer using the JDK jpackage tool.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root "source"
$Dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $Dist | Out-Null
if (-not (Get-Command jpackage -ErrorAction SilentlyContinue)) {{ throw "Install a full JDK 17+ containing jpackage. Windows EXE packaging may also require a compatible WiX Toolset." }}
$Jar = "{src.name}"
# jpackage builds the native installer on Windows; the JAR must declare Main-Class.
jpackage --type exe --name "{app_name}" --input $Source --main-jar $Jar --dest $Dist --app-version "1.0.0"{icon_arg}
if ($LASTEXITCODE -ne 0) {{ throw "jpackage failed with exit code $LASTEXITCODE" }}
$Expected = Join-Path $Dist "{app_name}-1.0.0.exe"
if (Test-Path $Expected) {{ Move-Item $Expected (Join-Path $Dist "{app_name}_Setup.exe") -Force }}
Write-Host "Build complete. Check the dist folder for {app_name}_Setup.exe."
'''
            (root / "build_windows.ps1").write_text(script, encoding="utf-8-sig")
            readme = f'''JAVA JAR -> WINDOWS SETUP

Run this kit on Windows.
1. Install a full JDK 17+ that includes jpackage.
2. Install a compatible WiX Toolset if required by your JDK's jpackage EXE packaging.
3. Ensure the JAR has a Main-Class manifest entry. External libraries should be in source\\lib and referenced by the manifest Class-Path.
4. Run in PowerShell: powershell -ExecutionPolicy Bypass -File .\\build_windows.ps1

Output: dist\\{app_name}_Setup.exe. {'A custom ICO icon is included.' if icon_path else 'No custom icon was selected.'}
'''
        else:
            entry_rel = _copy_project(src, source_dir, out_dir)
            (root / "entrypoint.txt").write_text(entry_rel.as_posix()+"\n", encoding="utf-8")
            (root / "app_name.txt").write_text(app_name+"\n", encoding="utf-8")
            script = r'''$ErrorActionPreference = "Stop"
# Build the Python project on Windows, then create a Setup.exe with Inno Setup.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { throw "Install Python 3 and ensure python is on PATH." }
if (-not (Get-Command ISCC.exe -ErrorAction SilentlyContinue)) { throw "Install Inno Setup 6/7 and ensure ISCC.exe is on PATH." }
$Venv = Join-Path $Root ".build-venv"
python -m venv $Venv
$Py = Join-Path $Venv "Scripts\python.exe"
& $Py -m pip install --upgrade pip
if (Test-Path (Join-Path $Root "source\requirements.txt")) { & $Py -m pip install -r (Join-Path $Root "source\requirements.txt") }
& $Py -m pip install "pyinstaller>=6.10,<7"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
& $Py (Join-Path $Root "build_python_windows.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$Name = (Get-Content (Join-Path $Root "app_name.txt") -Raw).Trim()
& ISCC.exe (Join-Path $Root "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
Write-Host "Build complete. Check the dist folder."
'''
            helper = r'''from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parent; SRC=ROOT/'source'; DIST=ROOT/'dist'; WORK=ROOT/'work'
ENTRY=(ROOT/'entrypoint.txt').read_text(encoding='utf-8').strip(); NAME=(ROOT/'app_name.txt').read_text(encoding='utf-8').strip()
EXCLUDED={'.git','.idea','.run','.venv','venv','env','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','tests','test','build','dist'}
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name',NAME,'--distpath',str(DIST),'--workpath',str(WORK),'--specpath',str(ROOT)]
icon=ROOT/'resources'/'app.ico'
if icon.is_file(): args += ['--icon',str(icon)]
for p in sorted(SRC.rglob('*')):
    if not p.is_file(): continue
    rel=p.relative_to(SRC)
    if any(part in EXCLUDED or part.startswith('.') for part in rel.parts[:-1]): continue
    if p.suffix.lower() in {'.pyc','.pyo','.spec','.iss','.exe','.dll','.msi'} or p.suffix.lower()=='.py': continue
    if p.name in {'requirements.txt','pyproject.toml','setup.py','setup.cfg','Thumbs.db','.DS_Store'}: continue
    args += ['--add-data',f'{p};{rel.parent.as_posix() if str(rel.parent) != "." else "."}']
subprocess.run(args+[str(SRC/ENTRY)],check=True,cwd=SRC)
'''
            (root / "build_windows.ps1").write_text(script, encoding="utf-8-sig")
            (root / "build_python_windows.py").write_text(helper, encoding="utf-8")
            icon_line = 'SetupIconFile="resources\\app.ico"\n' if icon_path else ""
            iss = f'''# Generated Inno Setup script for {app_name}
#define MyAppName "{app_name}"
#define MyAppVersion "1.0.0"
[Setup]
AppId={{{{A37C23E4-0A4A-4D8D-A1D8-4B5D9EAA1201}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher=Publisher
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
OutputDir=dist
OutputBaseFilename={app_name}_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion=1.0.0.0
VersionInfoProductVersion={{#MyAppVersion}}
{icon_line}
[Files]
Source: "dist\\{app_name}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{app_name}.exe"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{app_name}.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
'''
            (root / "installer.iss").write_text(iss, encoding="utf-8-sig")
            readme = f'''PYTHON PROJECT -> WINDOWS SETUP

Run this kit on Windows. Install Python 3 and Inno Setup 6/7; ensure python and ISCC.exe are on PATH. Run in PowerShell: powershell -ExecutionPolicy Bypass -File .\\build_windows.ps1

The script creates an isolated virtual environment, installs requirements.txt and PyInstaller, packages the project in directory mode, then compiles {app_name}_Setup.exe. {'A custom ICO icon is included.' if icon_path else 'No custom icon was selected.'} Dynamic imports may need extra PyInstaller configuration.
'''
        (root / "README_WINDOWS.txt").write_text(readme, encoding="utf-8")
        with zipfile.ZipFile(kit_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(root.rglob("*")):
                if p.is_file(): archive.write(p, p.relative_to(root.parent).as_posix())
    return kit_path
