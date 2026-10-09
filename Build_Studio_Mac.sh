#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo 'Run this script on macOS.' >&2
  exit 1
fi
python3 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r requirements.txt
.venv-mac/bin/python -c "from mac_backend import convert_icns; convert_icns('assets/logo.png','assets/app.icns')"
.venv-mac/bin/python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name ExeBuilderStudio --osx-bundle-identifier com.khurkham.exebuilderstudio \
  --icon "$PWD/assets/app.icns" --add-data "$PWD/assets:assets" \
  --add-data "$PWD/Ensure-Certificate.ps1:." --add-data "$PWD/SigningOperations.ps1:." \
  --distpath mac_dist --workpath mac_work --specpath mac_work main.py
.venv-mac/bin/python mac_backend.py mac_dist/ExeBuilderStudio.app mac_installer ExeBuilderStudio
printf '%s\n' 'Created: mac_installer/ExeBuilderStudio.dmg'
