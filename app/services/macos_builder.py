"""Create portable build kits for producing native macOS installers on a Mac.

Native macOS application bundles and DMG/PKG installers must be built on macOS.
This module prepares a ZIP kit; it does not pretend to compile a macOS installer on Windows.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
# Prepare a temporary macOS build kit; the actual DMG is built locally on a Mac.
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".idea", ".run", ".venv", "venv", "env", "ENV",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "tests", "test", "build", "dist", ".DS_Store",
}
EXCLUDED_NAMES = {
    ".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes",
    "pytest.ini", "mypy.ini", "ruff.toml", "tox.ini",
}
ENTRYPOINTS = ("main.py", "app.py", "run.py")


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]+", "", (value or "App")).strip(" .")
    name = re.sub(r"\s+", " ", name)
    return name or "App"


def _copy_project(source: Path, destination: Path, excluded_root: Path | None = None) -> Path:
    """Copy project runtime files while excluding common local/dev artifacts."""
    if source.is_file():
        if source.suffix.lower() != ".py":
            raise ValueError("For Python macOS builds, select a .py file or the whole project folder.")
        project = source.parent
        entry = source
    elif source.is_dir():
        project = source
        entry = next((project / name for name in ENTRYPOINTS if (project / name).is_file()), None)
        if entry is None:
            candidates = []
            for path in project.rglob("*.py"):
                rel = path.relative_to(project)
                if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
                    continue
                if path.name in ENTRYPOINTS:
                    candidates.append(path)
            if len(candidates) != 1:
                details = "\n".join(str(p.relative_to(project)) for p in candidates[:10])
                raise ValueError("Could not determine one Python entry file. Include main.py/app.py/run.py in the project root or select the entry .py file directly." + ("\nCandidates:\n" + details if details else ""))
            entry = candidates[0]
    else:
        raise ValueError("Select a valid Python file or project folder.")

    entry_rel = entry.relative_to(project)
    for path in project.rglob("*"):
        rel = path.relative_to(project)
        if excluded_root and project in excluded_root.parents and (path == excluded_root or excluded_root in path.parents):
            continue
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if path.is_dir():
            continue
        # Exclude local environment files, credentials, and private keys from generated build kits.
        lower_name = path.name.lower()
        if (path.name in EXCLUDED_NAMES or path.name.startswith("~$")
                or lower_name == ".env" or lower_name.startswith(".env.")
                or lower_name in {"credentials.json", "service-account.json", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
                or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".pyc", ".pyo", ".spec", ".iss", ".exe", ".dll", ".msi"}):
            continue
        # Do not copy the output ZIP or generated output folder back into the kit.
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    if not (destination / entry_rel).is_file():
        raise ValueError("The selected Python entry file was not included in the build kit.")
    return entry_rel


def create_macos_build_kit(*, kind: str, source: str, output: str, name: str, icon: str = "") -> Path:
    """Create a ZIP kit that builds a native macOS DMG on a Mac."""
    from app.services.icon_support import prepare_icon
    if kind not in {"java", "python"}:
        raise ValueError("Unknown macOS build type.")
    src = Path(source).expanduser().resolve() if source else None
    if not src or not src.exists():
        raise ValueError("Select a source JAR or Python project folder/file.")
    app_name = _safe_name(name)
    out_dir = Path(output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    kit_path = out_dir / f"{app_name}_macOS_Build_Kit.zip"
    if kit_path.exists():
        raise ValueError("The macOS build kit already exists. Choose another output folder or rename the app.")

    with tempfile.TemporaryDirectory(prefix="ebs_macos_kit_") as temp:
        root = Path(temp) / f"{app_name}_macOS_Build_Kit"
        source_dir = root / "source"
        source_dir.mkdir(parents=True)
        resources = root / "resources"
        resources.mkdir()
        icon_path = prepare_icon(icon, resources / "app.icns", "macos") if icon else None
        if kind == "java":
            if not src.is_file() or src.suffix.lower() != ".jar":
                raise ValueError("Select a Java .jar file.")
            shutil.copy2(src, source_dir / src.name)
            sibling_lib = src.parent / "lib"
            if sibling_lib.is_dir():
                shutil.copytree(sibling_lib, source_dir / "lib", ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
            main_jar = src.name
            icon_arg = ' --icon "$ROOT/resources/app.icns"' if icon_path else ""
            script = f'''#!/bin/bash
set -euo pipefail
# Build a native macOS DMG installer with the JDK jpackage tool.
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source"
DIST="$ROOT/dist"
mkdir -p "$DIST"
if ! command -v jpackage >/dev/null 2>&1; then
  echo "ERROR: Install a full JDK 17+ containing jpackage and ensure it is on PATH."
  exit 1
fi
# jpackage builds a native installer on macOS; the JAR must declare Main-Class.
jpackage --type dmg --name "{app_name}" --input "$SRC" --main-jar "{main_jar}" --dest "$DIST" --app-version "1.0.0"{icon_arg}
if [ -f "$DIST/{app_name}.dmg" ]; then mv "$DIST/{app_name}.dmg" "$DIST/{app_name}_Setup.dmg"; fi
echo "Done: $DIST/{app_name}_Setup.dmg"
'''
            requirements = f'''JAVA JAR -> macOS SETUP

On the Mac used to build:
1. Install a full JDK 17 or newer that includes jpackage.
2. Ensure java and jpackage are available (java -version, jpackage --version).
3. Run: bash build_macos.sh

Output: dist/{app_name}_Setup.dmg. The JAR must have a Main-Class manifest entry. If it depends on external libraries, keep them in source/lib and ensure the manifest Class-Path references them.
{'An app icon is included as resources/app.icns.' if icon_path else 'No custom app icon was selected.'}

The installer is built on macOS, not Windows.
'''
        else:
            entry_rel = _copy_project(src, source_dir, out_dir)
            (root / "entrypoint.txt").write_text(entry_rel.as_posix() + "\n", encoding="utf-8")
            (root / "app_name.txt").write_text(app_name + "\n", encoding="utf-8")
            script = '''#!/bin/bash
set -euo pipefail
# Package the Python project into a macOS .app and DMG using PyInstaller.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
# Prefer the validated interpreter selected/detected by ExeBuilderStudio.
PYTHON_BIN="${EBS_PYTHON:-$(command -v python3 || true)}"
if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
  echo "ERROR: Python 3 was not found. Install Python 3.11 or 3.12 on this Mac."
  exit 1
fi
"$PYTHON_BIN" -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
if [ -f source/requirements.txt ]; then python -m pip install -r source/requirements.txt; fi
python -m pip install "pyinstaller>=6.10,<7"
python build_python_macos.py
'''
            helper = r'''"""Build the copied Python project as a macOS .app and package a DMG."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parent; SRC=ROOT/'source'; DIST=ROOT/'dist'; WORK=ROOT/'work'
ENTRY=(ROOT/'entrypoint.txt').read_text(encoding='utf-8').strip(); NAME=(ROOT/'app_name.txt').read_text(encoding='utf-8').strip()
EXCLUDED={'.git','.idea','.run','.venv','venv','env','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','tests','test','build','dist','.build-venv'}
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name',NAME,'--distpath',str(DIST),'--workpath',str(WORK),'--specpath',str(ROOT)]
icon=ROOT/'resources'/'app.icns'
if icon.is_file(): args += ['--icon',str(icon)]
for path in sorted(SRC.rglob('*')):
    if not path.is_file(): continue
    rel=path.relative_to(SRC)
    if any(part in EXCLUDED or part.startswith('.') for part in rel.parts[:-1]): continue
    if path.suffix.lower() in {'.pyc','.pyo','.spec','.iss','.exe','.dll','.msi'}: continue
    if path.suffix.lower()=='.py' or path.name in {'requirements.txt','pyproject.toml','setup.py','setup.cfg','.gitignore','.DS_Store','Thumbs.db'}: continue
    args += ['--add-data',f'{path}:{rel.parent.as_posix() if str(rel.parent) != "." else "."}']
args.append(str(SRC/ENTRY)); subprocess.run(args,check=True,cwd=SRC)
app=DIST/f'{NAME}.app'
if not app.exists(): raise SystemExit(f'PyInstaller did not create expected app bundle: {app}')
dmg=DIST/f'{NAME}_Setup.dmg'
if dmg.exists(): dmg.unlink()
subprocess.run(['hdiutil','create','-volname',NAME,'-srcfolder',str(app),'-ov','-format','UDZO',str(dmg)],check=True)
print(f'Done: {dmg}')
'''
            (root / "build_python_macos.py").write_text(helper, encoding="utf-8")
            requirements = f'''PYTHON PROJECT -> macOS SETUP

On the Mac used to build:
1. Install Python 3 compatible with the project.
2. Run: bash build_macos.sh
3. The script creates an isolated environment, installs requirements.txt when present, installs PyInstaller, packages the project as a .app, then creates dist/{app_name}_Setup.dmg.

The Python project is packaged in directory mode. {'The app icon is included as resources/app.icns.' if icon_path else 'No custom app icon was selected.'}
Review requirements.txt for Windows-only packages. Dynamic imports or unusual resource paths may need extra PyInstaller configuration.
'''
        (root / "build_macos.sh").write_text(script, encoding="utf-8", newline="\n")
        (root / "README_MACOS.txt").write_text(requirements, encoding="utf-8", newline="\n")
        with zipfile.ZipFile(kit_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file(): archive.write(path, path.relative_to(root.parent).as_posix())
    return kit_path
