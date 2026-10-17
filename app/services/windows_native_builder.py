"""Build Windows Setup.exe installers locally without PowerShell or WiX.

Java applications are staged with jpackage --type app-image, then Inno Setup
creates the final installer. Python applications use PyInstaller --onedir,
then Inno Setup creates the final installer.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.services.icon_support import prepare_icon
from app.services.installer_builder import prepare_installer_build
from app.services.python_builder import prepare_python_build
from backend import safe_name


def _jdk_search_candidates(java_executable: str = "") -> list[Path]:
    """Collect likely JDK homes without assuming `java.exe` is a full JDK."""
    candidates: list[Path] = []

    # Explicit configuration is preferred, but an invalid JAVA_HOME must not stop discovery.
    configured_home = os.environ.get("JAVA_HOME", "").strip().strip('"')
    if configured_home:
        candidates.append(Path(configured_home).expanduser())

    # Resolve the selected Java executable and PATH entry. Oracle's `javapath` may be
    # only a launcher shim, so test both the original and resolved paths.
    executable_values = [java_executable, shutil.which("java") or ""]
    for value in executable_values:
        if not value:
            continue
        raw = Path(value).expanduser()
        for executable in (raw, raw.resolve()):
            if executable.name.lower() in {"java", "java.exe"}:
                candidates.append(executable.parent.parent)

    # Scan common JDK installation locations. This also finds JDKs installed by
    # Temurin, Oracle, Microsoft, Corretto, Zulu, and user-level package installers.
    roots = []
    for variable, fallback in (("ProgramFiles", r"C:\Program Files"),
                               ("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                               ("LOCALAPPDATA", "")):
        value = os.environ.get(variable, fallback)
        if value:
            base = Path(value)
            roots.extend([base / "Java", base / "Eclipse Adoptium", base / "Microsoft",
                          base / "Amazon Corretto", base / "BellSoft", base / "Zulu",
                          base / "AdoptOpenJDK", base / "Oracle", base / "Programs" / "Eclipse Adoptium",
                          base / "Programs" / "Microsoft", base / "Programs" / "Java"])
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for child in root.iterdir():
                if child.is_dir():
                    candidates.append(child)
                    # Handle nested layouts such as Java/jdk-25.0.3/Contents/Home.
                    candidates.append(child / "Contents" / "Home")
        except OSError:
            continue

    # Keep ordering stable and remove duplicates before validating the JDK tool.
    unique = []
    seen = set()
    for candidate in candidates:
        try:
            key = str(candidate.resolve()).casefold()
        except OSError:
            key = str(candidate).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_jdk_home(java_executable: str = "") -> str:
    """Return a JDK home only when it contains the required jpackage executable."""
    for home in _jdk_search_candidates(java_executable):
        if (home / "bin" / "jpackage.exe").is_file():
            return str(home.resolve())
    return ""


def _find_jpackage(jdk_home: str = "") -> str:
    """Find jpackage in the selected JDK first, then fall back to discovery."""
    if jdk_home:
        selected = Path(jdk_home).expanduser()
        tool = selected / "bin" / "jpackage.exe"
        if not tool.is_file():
            raise FileNotFoundError(f"The selected JDK does not contain jpackage.exe: {selected}")
        from app.services.jdk_manager import validate_jdk_home
        valid, detail = validate_jdk_home(selected, executable_name="jpackage.exe")
        if not valid:
            raise FileNotFoundError(detail)
        return str(tool.resolve())
    found = shutil.which("jpackage") or shutil.which("jpackage.exe")
    if found and Path(found).is_file():
        return str(Path(found).resolve())

    home = resolve_jdk_home()
    if home:
        return str(Path(home) / "bin" / "jpackage.exe")

    java = shutil.which("java") or ""
    if java:
        try:
            version = subprocess.run([java, "-version"], capture_output=True, text=True,
                                     timeout=8, encoding="utf-8", errors="replace")
            detail = (version.stderr or version.stdout).splitlines()
            detected = detail[0].strip() if detail else "Java was detected, but jpackage was not found."
        except (OSError, subprocess.SubprocessError):
            detected = "Java was detected, but jpackage was not found."
        raise FileNotFoundError(
            "A Java runtime was found (" + detected + "), but a full JDK containing jpackage.exe was not found. "
            "Install a full JDK 17 or newer (for example, Temurin JDK), then set JAVA_HOME to the JDK folder, "
            "such as C:\\Program Files\\Eclipse Adoptium\\jdk-21... . Do not set JAVA_HOME to "
            "Common Files\\Oracle\\Java\\javapath or to the bin folder."
        )
    raise FileNotFoundError(
        "A full JDK 17 or newer containing jpackage.exe was not found. Install a JDK, then set JAVA_HOME "
        "to the JDK root folder (not its bin folder and not Oracle\\Java\\javapath)."
    )


def _find_iscc(compiler: str = "") -> str:
    """Find Inno Setup compiler from the configured path or standard installs."""
    candidates = [Path(compiler)] if compiler else []
    for root in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        candidates.extend(Path(root) / f"Inno Setup {version}" / "ISCC.exe" for version in ("7", "6"))
    found = shutil.which("ISCC.exe")
    if found:
        candidates.insert(0, Path(found))
    for candidate in candidates:
        if candidate.is_file() and candidate.name.lower() == "iscc.exe":
            return str(candidate.resolve())
    raise FileNotFoundError("Inno Setup compiler (ISCC.exe) was not found. Install Inno Setup 6/7 or ensure ISCC.exe is available in a standard installation folder or PATH.")


def _run(command: list[str], *, cwd: Path, log=None, env=None, progress=None,
         progress_range=None, phase="Building", process_callback=None) -> None:
    """Run a native tool, stream its output, and report estimated progress."""
    # Popen streams build output live instead of waiting for the entire command to finish.
    start, end = progress_range or (0, 0)
    if progress and progress_range:
        progress(start, phase)
    lines = []
    # Hide the child console window on Windows while continuing to capture and
    # stream stdout/stderr into the application's log panel.
    no_console = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        command, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
        creationflags=no_console
    )
    if process_callback:
        process_callback(process)
    try:
        if process.stdout is not None:
            for line in process.stdout:
                lines.append(line)
                if log:
                    log(line)
                # Tool output does not expose a universal percentage; line-based movement is an estimate.
                if progress and progress_range:
                    current = min(end - 1, start + len(lines))
                    progress(current, phase)
        return_code = process.wait()
    finally:
        if process_callback:
            process_callback(None)
        if process.stdout is not None:
            process.stdout.close()
    output = "".join(lines).strip()
    if return_code:
        detail = output or "No diagnostic output."
        raise RuntimeError(f"Command failed ({return_code}): {Path(command[0]).name}\n{detail}")
    if progress and progress_range:
        progress(end, phase)


def _write_java_installer_script(app_image: Path, name: str, output: Path, icon: str = "") -> Path:
    """Create an Inno Setup script to install the jpackage app-image directory."""
    executable = app_image / f"{name}.exe"
    if not executable.is_file():
        raise RuntimeError(f"jpackage app-image did not contain {name}.exe")
    # Quote paths and names for Inno Setup's string syntax.
    def quote(value: str | Path) -> str:
        return '"' + str(value).replace('"', '""') + '"'
    script = app_image.parent / "java_installer.iss"
    lines = [
        "; Generated by ExeBuilderStudio. The application image includes its runtime.",
        "#define MyAppName " + quote(name),
        "#define MyAppVersion \"1.0.0\"",
        "[Setup]",
        "AppId={{A37C23E4-0A4A-4D8D-A1D8-4B5D9EAA1201}}",
        "AppName={#MyAppName}",
        "AppVersion={#MyAppVersion}",
        "DefaultDirName={localappdata}\\Programs\\{#MyAppName}",
        "DefaultGroupName={#MyAppName}",
        "PrivilegesRequired=lowest",
        "OutputDir=" + quote(output),
        "OutputBaseFilename=" + name + "_Setup",
        "Compression=lzma2",
        "SolidCompression=yes",
        "WizardStyle=modern",
    ]
    if icon:
        # jpackage accepts an ICO file; also use it for the installer wizard.
        lines.append("SetupIconFile=" + quote(icon))
    lines += [
        "[Tasks]",
        'Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked',
        "[Files]",
        "Source: " + quote(app_image / "*") + '; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs',
        "[Icons]",
        'Name: "{group}\\{#MyAppName}"; Filename: "{app}\\' + name + '.exe"',
        'Name: "{userdesktop}\\{#MyAppName}"; Filename: "{app}\\' + name + '.exe"; Tasks: desktopicon',
        "[Run]",
        'Filename: "{app}\\' + name + '.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent',
        "",
    ]
    script.write_text("\n".join(lines), encoding="utf-8-sig")
    return script


def build_windows_installer(*, kind: str, source: str, output: str, name: str,
                            icon: str = "", interpreter: str = "", compiler: str = "",
                            log=None, jdk_home: str = "", overwrite: bool = False,
                            progress=None, process_callback=None) -> Path:
    """Create the final *_Setup.exe directly in the selected output folder."""
    if os.name != "nt":
        raise OSError("Windows Setup.exe installers must be built on Windows.")
    if kind not in {"java", "python"}:
        raise ValueError("Unknown application type.")
    source_path = Path(source).expanduser().resolve() if source else None
    if not source_path or not source_path.exists():
        raise ValueError("Select a valid source JAR or Python project/file.")
    app_name = safe_name(name)
    output_dir = Path(output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{app_name}_Setup.exe"
    if target.exists() and not overwrite:
        raise FileExistsError(f"Output file already exists: {target}. Confirm overwrite or choose another folder/name.")
    iscc = _find_iscc(compiler)

    with tempfile.TemporaryDirectory(prefix="ebs_windows_build_") as temp:
        work = Path(temp)
        # Build to a staging folder so a failed rebuild never damages the existing installer.
        staged_output = work / "installer-output"
        staged_output.mkdir(parents=True, exist_ok=True)
        if kind == "java":
            if not source_path.is_file() or source_path.suffix.lower() != ".jar":
                raise ValueError("Select a Java .jar file.")
            jpackage = _find_jpackage(jdk_home)
            source_dir = work / "source"
            source_dir.mkdir()
            shutil.copy2(source_path, source_dir / source_path.name)
            # Preserve sibling lib/ dependencies used by the JAR manifest Class-Path.
            library_dir = source_path.parent / "lib"
            if library_dir.is_dir():
                shutil.copytree(library_dir, source_dir / "lib", dirs_exist_ok=True)
            image_dir = work / "app-image"
            command = [jpackage, "--type", "app-image", "--name", app_name,
                       "--input", str(source_dir), "--main-jar", source_path.name,
                       "--dest", str(image_dir), "--app-version", "1.0.0"]
            icon_path = ""
            if icon:
                icon_path = str(prepare_icon(icon, work / "resources" / "app.ico", "windows"))
                command += ["--icon", icon_path]
            # app-image avoids jpackage's WiX-based EXE installer path.
            # Pin JAVA_HOME/PATH to the JDK selected by the user for this build.
            build_env = os.environ.copy()
            active_jdk = jdk_home or resolve_jdk_home()
            if active_jdk:
                build_env["JAVA_HOME"] = str(Path(active_jdk).resolve())
                build_env["PATH"] = str(Path(active_jdk).resolve() / "bin") + os.pathsep + build_env.get("PATH", "")
            if progress:
                progress(12, "Preparing Java application")
            _run(command, cwd=work, log=log, env=build_env, progress=progress,
                 progress_range=(15, 60), phase="Packaging Java application", process_callback=process_callback)
            app_image = image_dir / app_name
            script = _write_java_installer_script(app_image, app_name, staged_output, icon_path)
            _run([iscc, str(script)], cwd=work, log=log, progress=progress,
                 progress_range=(68, 92), phase="Creating installer with Inno Setup", process_callback=process_callback)
        else:
            py = interpreter or ""
            if not py and getattr(os.sys, "frozen", False):
                bundled_python = Path(os.sys.executable).resolve().parent / "tools" / "python" / "python.exe"
                if bundled_python.is_file():
                    py = str(bundled_python)
            if not py:
                py = shutil.which("python") or shutil.which("python3") or ""
            if not py or not Path(py).is_file():
                raise FileNotFoundError("Python 3 was not found. Install Python, select its interpreter, or use a Full Offline installer with the Python runtime bundled.")
            icon_path = ""
            if icon:
                icon_path = str(prepare_icon(icon, work / "resources" / "app.ico", "windows"))
            job = prepare_python_build(interpreter=py, source=str(source_path),
                                       output=str(work / "python-build"), name=app_name,
                                       console=False, icon=icon_path)
            if progress:
                progress(12, "Preparing Python application")
            _run([py, *job["args"]], cwd=Path(job["cwd"]), log=log, progress=progress,
                 progress_range=(15, 60), phase="Packaging Python application", process_callback=process_callback)
            compiler_job = prepare_installer_build(
                compiler=iscc, release_folder=job["dist_dir"] / app_name,
                exe_name=f"{app_name}.exe", name=app_name, version="1.0",
                publisher="ExeBuilderStudio", output=staged_output, icon=icon_path)
            _run([compiler_job["executable"], *compiler_job["args"]], cwd=staged_output, log=log,
                 progress=progress, progress_range=(68, 92),
                 phase="Creating installer with Inno Setup", process_callback=process_callback)

        if progress:
            progress(96, "Publishing installer")
        staged_target = staged_output / target.name
        if not staged_target.is_file():
            raise RuntimeError("Build completed without creating the expected installer: " + str(staged_target))
        # Publish only after a successful build. Copy to the output volume, then replace atomically.
        publish_temp = output_dir / ("." + target.name + ".new")
        try:
            shutil.copy2(staged_target, publish_temp)
            os.replace(publish_temp, target)
        finally:
            try:
                publish_temp.unlink(missing_ok=True)
            except OSError:
                pass
    return target
