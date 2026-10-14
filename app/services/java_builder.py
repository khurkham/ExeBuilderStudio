"""Prepare Java JAR-to-EXE build jobs without depending on the UI layer."""
# Validate Java inputs and prepare the local jpackage/Launch4j job.
from pathlib import Path
import shutil

from backend import java_candidates, launch_config, require_file, safe_name


def prepare_java_build(*, source, output, name, icon='', minimum='17', jre='', console=False, tool=''):
    # Validate inputs before creating output files or launching external tools.
    jar = require_file(source, '.jar')
    output_dir = Path(output).resolve()
    app_name = safe_name(name)
    launch4j = str(Path(tool).resolve()) if tool else ''
    if not launch4j or not Path(launch4j).is_file():
        raise ValueError('Select a valid Launch4j command-line executable.')

    # Keep each release isolated so an existing build is never overwritten.
    release_dir = output_dir / app_name
    if release_dir.exists() and any(release_dir.iterdir()):
        raise ValueError('Release folder exists. Choose a new output folder or name.')
    release_dir.mkdir(parents=True, exist_ok=True)

    # Bundle a local JRE only when the user explicitly selects one.
    if jre:
        jre_dir = Path(jre).resolve()
        if not (jre_dir / 'bin' / 'java.exe').is_file():
            raise ValueError('Java folder must contain bin/java.exe')
        if jre_dir == release_dir or jre_dir in release_dir.parents:
            raise ValueError('Java source cannot contain output folder')
        shutil.copytree(jre_dir, release_dir / 'jre', dirs_exist_ok=True)

    # Include adjacent libraries for JARs that use a manifest Class-Path.
    lib_dir = jar.parent / 'lib'
    if lib_dir.is_dir():
        shutil.copytree(lib_dir, release_dir / 'lib', dirs_exist_ok=True)

    # Generate Launch4j configuration and return the process job to the UI.
    target = release_dir / f'{app_name}.exe'
    config = launch_config(jar, target, icon, minimum, bool(jre), console)
    return {'executable': launch4j, 'args': [str(config)], 'cwd': release_dir,
            'release_dir': release_dir, 'target': target}
