"""Discover and validate installed JDKs for user-selectable Java builds."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _jdk_executable(home: Path) -> Path:
    """Return the platform-specific jpackage path inside a JDK home."""
    name = "jpackage.exe" if os.name == "nt" else "jpackage"
    return home / "bin" / name


def jdk_version(home: str | Path) -> str:
    """Read the JDK release metadata without invoking a shell."""
    path = Path(home).expanduser()
    release = path / "release"
    if release.is_file():
        try:
            content = release.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'^JAVA_VERSION="?([^"\n]+)', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        except OSError:
            pass
    executable = _jdk_executable(path)
    if executable.is_file():
        try:
            result = subprocess.run([str(executable), "--version"], capture_output=True,
                                    text=True, timeout=5, encoding="utf-8", errors="replace")
            text = (result.stdout or result.stderr).strip()
            match = re.search(r"(?:jpackage|openjdk)\s+(\d+(?:\.\d+){0,3})", text, re.I)
            if match:
                return match.group(1)
        except (OSError, subprocess.SubprocessError):
            pass
    return "Unknown version"


def validate_jdk_home(home: str | Path, minimum_major: int = 17, executable_name: str | None = None) -> tuple[bool, str]:
    """Require a full JDK with jpackage and a supported major version."""
    path = Path(home).expanduser()
    if not path.is_dir():
        return False, "Selected JDK folder does not exist."
    executable = path / "bin" / (executable_name or _jdk_executable(path).name)
    if not executable.is_file():
        return False, f"No jpackage executable was found in: {path / 'bin'}"
    version = jdk_version(path)
    match = re.match(r"(\d+)", version)
    if not match or int(match.group(1)) < minimum_major:
        return False, f"JDK 17 or newer is required; selected version: {version}."
    return True, version


def bundled_jdk_home() -> Path | None:
    """Return the optional JDK bundled inside a packaged macOS app."""
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return None
    try:
        # PyInstaller app executable lives in Contents/MacOS; tools live in Contents/Resources.
        contents = Path(sys.executable).resolve().parent.parent
        candidate = contents / "Resources" / "tools" / "jdk"
        if _jdk_executable(candidate).is_file():
            return candidate
    except OSError:
        pass
    return None


def discover_jdk_homes() -> list[tuple[str, str]]:
    """Find installed or optionally bundled JDK homes and return display/path pairs."""
    candidates: list[Path] = []
    bundled = bundled_jdk_home()
    if bundled:
        candidates.append(bundled)
    configured = os.environ.get("JAVA_HOME", "").strip().strip('"')
    if configured:
        candidates.append(Path(configured).expanduser())

    if os.name == "nt":
        roots = []
        for variable, fallback in (("ProgramFiles", r"C:\Program Files"),
                                   ("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                                   ("LOCALAPPDATA", "")):
            value = os.environ.get(variable, fallback)
            if value:
                base = Path(value)
                roots.extend([base / "Java", base / "Eclipse Adoptium", base / "Microsoft",
                              base / "Amazon Corretto", base / "BellSoft", base / "Zulu",
                              base / "AdoptOpenJDK", base / "Oracle",
                              base / "Programs" / "Eclipse Adoptium", base / "Programs" / "Java"])
        for root in roots:
            if root.is_dir():
                try:
                    candidates.extend(p for p in root.iterdir() if p.is_dir())
                except OSError:
                    continue
    elif sys.platform == "darwin":
        candidates.extend(Path("/Library/Java/JavaVirtualMachines").glob("*.jdk/Contents/Home"))
        candidates.extend(Path("/opt/homebrew/opt").glob("openjdk*/libexec/openjdk.jdk/Contents/Home"))
        candidates.extend(Path("/usr/local/opt").glob("openjdk*/libexec/openjdk.jdk/Contents/Home"))

    unique: dict[str, tuple[str, str]] = {}
    for candidate in candidates:
        try:
            home = candidate.resolve()
        except OSError:
            home = candidate
        ok, version = validate_jdk_home(home)
        if not ok:
            continue
        unique[str(home).casefold()] = (f"JDK {version} — {home}", str(home))
    return sorted(unique.values(), key=lambda item: tuple(int(x) for x in re.findall(r"\d+", item[0].split(" — ", 1)[0])), reverse=True)
