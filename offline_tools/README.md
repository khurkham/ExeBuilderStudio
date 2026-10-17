# Offline installer payloads (publisher/build-machine staging)

The Offline mode is intentionally fail-closed: it will not label an installer as Offline unless its required payload folders exist. This folder is a staging layout, not a collection of third-party binaries; no JDK/Python binaries are redistributed in this source ZIP.

## Windows

Prepare these folders before running `Build_Studio.ps1 -CreateInstaller -Mode Offline`:

- `offline_tools/windows/wheelhouse/` — all wheels needed by `requirements.txt`, PyInstaller, and transitive dependencies for the build Python version/architecture.
- `offline_tools/windows/jdk/` — extracted, redistributable JDK 17+ with `bin/jpackage.exe`.
- `offline_tools/windows/python/` — a complete Python runtime with `python.exe` and pip, compatible with your app's target build workflow.
- `offline_tools/windows/inno/` — Inno Setup compiler payload including `ISCC.exe` (build-time compiler is still selected with `-ISCC`; this copy is staged for the installed app's bundled tool payload).

The build stages JDK/Python/Inno payloads into `dist/ExeBuilderStudio/tools` before compiling the installer, so Inno Setup only packages files that actually exist. Bundled JDK discovery is enabled. The app's Python build selection and project dependency installation still need runtime validation before claiming arbitrary Python projects can be built fully offline.

## macOS

Run `EBS_INSTALLER_MODE=Offline` on the Mac architecture you are packaging for. Set:

- `EBS_WHEELHOUSE` (defaults to `offline_tools/macos/wheelhouse`) containing all compatible wheels for `requirements.txt` and PyInstaller.
- `EBS_BUNDLE_JDK_HOME` to a redistributable JDK 17+ for the current architecture.
- `EBS_OFFLINE_PYTHON_HOME` to a complete Python installation containing `bin/python3` (and pip), suitable for building user Python projects.

The script includes JDK and Python under `ExeBuilderStudio.app/Contents/Resources/tools`. It does not download tools in Offline mode. `hdiutil` is provided by macOS. Build separately on Apple Silicon and Intel unless using verified universal binaries.

## Standard mode

Standard mode uses the existing online dependency setup and creates an installer with a `Standard` filename. The installed app can still use its existing tool detection/download workflow.

## Security and licensing

Only stage binaries obtained from official publishers. Verify publisher checksums/signatures and review redistribution terms before distributing an Offline installer. Do not put credentials or signing private keys in these folders.
