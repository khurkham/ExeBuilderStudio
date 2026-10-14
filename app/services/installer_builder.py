"""Prepare Inno Setup installer compilation jobs."""
from pathlib import Path
from backend import inno_script, safe_name


def prepare_installer_build(*, compiler, release_folder, exe_name, name, version,
                            publisher, output, icon=''):
    # Validate compiler and release directory before generating an installer script.
    iscc = str(Path(compiler).resolve()) if compiler else ''
    if not iscc or not Path(iscc).is_file():
        raise ValueError('Select a valid Inno Setup compiler (ISCC.exe).')
    if not release_folder or not Path(release_folder).is_dir():
        raise ValueError('Select a release folder')
    folder = Path(release_folder).resolve()
    out = Path(output).resolve()

    # Keep installer output outside the release folder to avoid recursive packaging.
    if out == folder or folder in out.parents:
        raise ValueError('Installer output must be outside the release folder')
    if Path(exe_name).name != exe_name or '/' in exe_name or '\\' in exe_name:
        raise ValueError('Enter EXE filename only')
    app_name = safe_name(name)

    # Generate the Inno Setup script and return the compiler job for the UI.
    script = inno_script(folder, exe_name, app_name, version, publisher, out, icon)
    target = out / f'{app_name}_Setup.exe'
    return {'executable': iscc, 'args': [str(script)], 'cwd': out,
            'script': script, 'release_exe': folder / exe_name, 'target': target}
