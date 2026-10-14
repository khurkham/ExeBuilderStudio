"""Prepare Python project builds with automatic resource collection."""
# Validate Python inputs and generate a PyInstaller job without bundling development files or secrets.
from pathlib import Path
import os

from backend import require_file, safe_name

# Folders used only by editors, virtual environments, tests, or previous builds.
EXCLUDED_DIRS = {
    ".git", ".idea", ".run", ".venv", "venv", "env", "ENV",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", "tests", "test", "build", "dist",
}
# Project-management files are not runtime resources. Other data files are kept.
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".spec", ".iss"}
EXCLUDED_NAMES = {"requirements.txt", "pyproject.toml", "setup.py",
                  "setup.cfg", "tox.ini", ".gitignore", ".gitattributes",
                  "Pipfile", "Pipfile.lock", "poetry.lock", "uv.lock",
                  "pytest.ini", "mypy.ini", "ruff.toml", ".DS_Store", "Thumbs.db"}
ENTRYPOINT_NAMES = ("main.py", "app.py", "run.py")

def _project_entrypoint(project: Path, output_dir: Path | None = None) -> Path:
    # Prefer conventional entry points in the project root.
    for name in ENTRYPOINT_NAMES:
        candidate = project / name
        if candidate.is_file():
            return candidate

    # Search common source folders while skipping generated and development folders.
    candidates = []
    for path in project.rglob("*.py"):
        relative = path.relative_to(project)
        if output_dir and (path == output_dir or output_dir in path.parents):
            continue
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            continue
        if path.name in ENTRYPOINT_NAMES:
            candidates.append(path)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("No main.py, app.py, or run.py found. Select the entry Python file instead.")
    options = "\n".join(str(p.relative_to(project)) for p in candidates[:10])
    raise ValueError("Several possible entry files were found. Select the main .py file directly:\n" + options)

def _add_project_resources(args, project: Path, output_dir: Path):
    # Add runtime resources while excluding IDE settings, virtual environments, tests,
    # generated builds, Python source files, and common project configuration files.
    separator = ";" if os.name == "nt" else ":"
    for path in sorted(project.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project)
        # Never bundle files generated into the selected output directory.
        if path == output_dir or output_dir in path.parents:
            continue
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES or path.suffix.lower() == ".py":
            continue
        if path.name in EXCLUDED_NAMES or path.name.startswith("~$"):
            continue
        # Keep each resource at its original relative path inside the packaged app.
        destination = relative.parent.as_posix()
        if destination == ".":
            destination = "."
        args += ["--add-data", f"{path}{separator}{destination}"]

def prepare_python_build(*, interpreter, source, output, name,
                         console=False, icon='', data='', hidden=''):
    # Validate the interpreter and application name before creating a build job.
    python = str(Path(interpreter).resolve()) if interpreter else ''
    if not python or not Path(python).is_file():
        raise ValueError('Select a valid Python interpreter.')

    selected = Path(source).expanduser().resolve() if source else Path()
    if not source or not selected.exists():
        raise ValueError("Select a Python entry file or project folder.")
    # Accept either a whole project folder or a single Python entry file.
    project = selected if selected.is_dir() else selected.parent
    output_dir = Path(output).resolve()
    if selected.is_dir():
        script = _project_entrypoint(project, output_dir)
    else:
        script = require_file(selected, '.py')
    app_name = safe_name(name)

    # Refuse to overwrite an existing PyInstaller executable or application folder.
    dist_dir = output_dir / 'dist'
    if (dist_dir / app_name).exists() or (dist_dir / f'{app_name}.exe').exists():
        raise ValueError('Output exists. Select a new output folder or name.')

    # Keep generated spec files, temporary work files, and final output separated.
    args = ['-m', 'PyInstaller', '--noconfirm', '--clean', '--name', app_name,
            '--distpath', str(dist_dir), '--workpath', str(output_dir / 'work'),
            '--specpath', str(output_dir), '--onedir']
    if not console:
        args.append('--windowed')
    if icon:
        args += ['--icon', str(require_file(icon, '.ico'))]

    # Automatically collect project resources even when the user selected main.py.
    # Development folders and generated outputs are excluded by _add_project_resources.
    _add_project_resources(args, project, output_dir)

    # Preserve compatibility with callers that provide an external resource folder.
    if data:
        data_dir = Path(data).resolve()
        if not data_dir.is_dir():
            raise ValueError('Invalid data folder')
        if data_dir == output_dir or data_dir in output_dir.parents:
            raise ValueError('Data folder cannot contain build output')
        separator = ';' if os.name == 'nt' else ':'
        for path in sorted(data_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(data_dir)
            if any(part in EXCLUDED_DIRS or part.startswith(".") for part in rel.parts[:-1]):
                continue
            if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name in EXCLUDED_NAMES:
                continue
            args += ['--add-data', f'{path}{separator}{(Path(data_dir.name) / rel.parent).as_posix()}']

    # Preserve optional hidden imports for projects with dynamic module loading.
    for module in hidden.split(','):
        if module.strip():
            args += ['--hidden-import', module.strip()]
    args.append(str(script))

    # Use the project root as the process directory when a folder was selected.
    working_dir = project or script.parent
    target = dist_dir / app_name / f'{app_name}.exe'
    return {'executable': python, 'args': args, 'cwd': working_dir,
            'output_dir': output_dir, 'dist_dir': dist_dir, 'target': target,
            'source': script, 'project_dir': project}
